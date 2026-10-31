"""
User Dashboard, ML Predictions, Transactions & AI Chat Routes.
Provides isolated, dynamic financial data per authenticated user.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from db.session import get_db
from db.models import (
    UserProfile, Transaction, Merchant, Product, SalesDaily, ChatMessage,
    Bill, MLTrainingSample,
)
from core.auth import get_current_user, get_current_merchant
from engine.ml_engine import (
    categorize_expense,
    is_anomaly,
    predict_future_spending,
    analyze_user_finances,
    train_models,
    train_from_db,
    get_model_status,
    CATEGORY_ORDER,
)
from ai.groq_client import ask_groq_assistant_ex

router = APIRouter(prefix="/api/user", tags=["user_dashboard"])
ml_router = APIRouter(prefix="/api/ml", tags=["ml"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _merchant_for(db: Session, current_user: UserProfile) -> Optional[Merchant]:
    return db.query(Merchant).filter(Merchant.user_id == current_user.id).first()


def _transaction_rows(db: Session, user_id: str) -> list[dict]:
    rows = db.query(Transaction).filter(
        Transaction.user_id == user_id
    ).order_by(Transaction.date.desc(), Transaction.created_at.desc()).all()
    return [
        {
            "id": t.id,
            "type": t.type,
            "category": t.category,
            "amount": t.amount,
            "description": t.description,
            "date": str(t.date),
            "is_anomaly": t.is_anomaly,
        }
        for t in rows
    ]


def _recent_bills(db: Session, merchant: Optional[Merchant]) -> list[dict]:
    if not merchant:
        return []
    rows = db.query(Bill).filter(
        Bill.merchant_id == merchant.id
    ).order_by(Bill.created_at.desc()).limit(5).all()
    return [
        {
            "id": b.id,
            "bill_ref": b.bill_ref,
            "file_name": b.file_name,
            "engine": b.ocr_engine,
            "confidence": b.ocr_confidence,
            "item_count": b.item_count,
            "total_amount": b.total_amount,
            "status": b.status,
            "created_at": str(b.created_at),
        }
        for b in rows
    ]


def _build_chat_context(
    db: Session,
    current_user: UserProfile,
    merchant: Optional[Merchant],
    analysis: dict,
    txns_data: list[dict],
) -> dict:
    """Assemble grounded business metrics for the AI assistant."""
    product_count = 0
    hot_products: list[dict] = []
    weak_day = None
    weak_day_dip = None
    sales_rows: list[SalesDaily] = []

    if merchant:
        product_count = db.query(Product).filter(
            Product.merchant_id == merchant.id,
            Product.is_active == True,  # noqa: E712
        ).count()
        sales_rows = db.query(SalesDaily).filter(
            SalesDaily.merchant_id == merchant.id
        ).all()

    if sales_rows:
        by_day: dict[str, list[float]] = {}
        for row in sales_rows:
            by_day.setdefault(row.weekday, []).append(float(row.total_amount or 0.0))
        averages = {day: (sum(vals) / len(vals) if vals else 0.0) for day, vals in by_day.items()}
        if averages:
            overall = sum(averages.values()) / len(averages)
            weak_day = min(averages, key=averages.get)
            if overall > 0:
                weak_day_dip = round((overall - averages[weak_day]) / overall * 100, 1)

        hot_products = []
        if merchant:
            try:
                from engine.analysis import get_product_insights
                insights = get_product_insights(db, merchant.id)
                hot_products = insights.get("top_products", [])[:3]
            except Exception:
                hot_products = []

    return {
        "shop_name": merchant.name if merchant else "My Shop",
        "shop_type": merchant.shop_type if merchant else "retail",
        "product_count": product_count,
        "has_sales": len(sales_rows) > 0,
        "has_sales_history": len(sales_rows) > 0,
        "total_income": analysis.get("total_income", 0.0),
        "total_expense": analysis.get("total_expense", 0.0),
        "balance": analysis.get("balance", current_user.balance),
        "monthly_budget": current_user.monthly_budget,
        "savings_rate_pct": analysis.get("savings_rate_pct", 0.0),
        "weak_day": weak_day,
        "weak_day_dip_pct": weak_day_dip,
        "top_products": hot_products,
        "predicted_30_days_total": analysis.get("predictions", {}).get("next_30_days_total", 0.0),
        "top_categories": analysis.get("categories", [])[:4],
        "monthly_trend": analysis.get("monthly_trend", []),
        "anomalies": analysis.get("anomalies", []),
        "anomaly_count": analysis.get("anomaly_count", 0),
        "transaction_count": len(txns_data),
        "recent_transactions": txns_data[:5],
        "recent_bills": _recent_bills(db, merchant),
    }


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@router.get("/dashboard")
def get_user_dashboard(
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
):
    """Dynamic dashboard: balance, spending, categories, trends and ML forecasts."""
    txns_data = _transaction_rows(db, current_user.id)
    analysis = analyze_user_finances(txns_data, monthly_budget=current_user.monthly_budget)
    merchant = _merchant_for(db, current_user)

    total_income = analysis["total_income"]
    total_expense = analysis["total_expense"]
    computed_balance = (
        current_user.balance
        if not txns_data and current_user.balance > 0
        else (total_income - total_expense)
    )

    predictions = analysis["predictions"]
    if not analysis.get("has_data"):
        trend_label = "new"
    elif predictions["next_30_days_total"] > current_user.monthly_budget > 0:
        trend_label = "rising"
    else:
        trend_label = "steady"

    return {
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "balance": round(computed_balance, 2),
            "language": current_user.language,
            "theme": current_user.theme,
            "monthly_budget": current_user.monthly_budget,
            "is_demo": current_user.is_demo,
        },
        "financials": {
            "balance": round(computed_balance, 2),
            "total_income": total_income,
            "total_expense": total_expense,
            "savings_rate_pct": analysis["savings_rate_pct"],
        },
        "financial_summary": {
            "total_income": total_income,
            "total_expense": total_expense,
            "net_savings": round(total_income - total_expense, 2),
            "savings_rate_pct": analysis["savings_rate_pct"],
            "monthly_budget": current_user.monthly_budget,
            "budget_spent_pct": round(
                (total_expense / current_user.monthly_budget * 100), 1
            ) if current_user.monthly_budget > 0 else 0.0,
            "has_data": analysis.get("has_data", bool(txns_data)),
        },
        "ml_predictions": {
            "predicted_7day_spending": predictions["next_7_days_total"],
            "predicted_30day_spending": predictions["next_30_days_total"],
            "trend": trend_label,
            "confidence_score": predictions["confidence_pct"],
        },
        "categories": analysis["categories"],
        "monthly_trend": analysis["monthly_trend"],
        "predictions": predictions,
        "anomaly_count": analysis["anomaly_count"],
        "anomalies_count": analysis["anomalies_count"],
        "anomalies": analysis["anomalies"],
        "insights": analysis["insights"],
        "recent_transactions": txns_data[:10],
        "recent_bills": _recent_bills(db, merchant),
        "merchant": (
            {"id": merchant.id, "name": merchant.name, "shop_type": merchant.shop_type}
            if merchant else None
        ),
        "has_data": analysis.get("has_data", False),
    }


@router.get("/transactions")
def get_user_transactions(
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
):
    """Full transaction ledger for the authenticated user."""
    return _transaction_rows(db, current_user.id)


class NewTransactionPayload(BaseModel):
    description: str = Field(..., min_length=1, max_length=255)
    amount: float = Field(..., gt=0)
    type: str = Field(default="expense", pattern="^(income|expense)$")
    category: Optional[str] = None
    date: Optional[str] = None


@router.post("/transactions")
def add_transaction(
    payload: NewTransactionPayload,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
):
    """Add a transaction with automatic ML category & anomaly detection."""
    category = payload.category
    if not category or category.strip().lower() == "auto":
        category = categorize_expense(payload.description)

    context_amounts = [
        float(t.amount) for t in db.query(Transaction).filter(
            Transaction.user_id == current_user.id,
            Transaction.type == "expense",
        ).all()
    ]
    anomaly_flag = is_anomaly(payload.amount, context_amounts)

    txn_date = date.today()
    if payload.date:
        try:
            txn_date = datetime.strptime(payload.date, "%Y-%m-%d").date()
        except ValueError:
            pass

    t = Transaction(
        id=f"tx_{uuid.uuid4().hex[:10]}",
        user_id=current_user.id,
        type=payload.type,
        category=category,
        amount=payload.amount,
        description=payload.description,
        date=txn_date,
        is_anomaly=anomaly_flag,
    )
    db.add(t)

    if payload.type == "income":
        current_user.balance += payload.amount
    else:
        current_user.balance -= payload.amount

    db.commit()
    db.refresh(t)

    return {
        "id": t.id,
        "type": t.type,
        "category": t.category,
        "amount": t.amount,
        "description": t.description,
        "date": str(t.date),
        "is_anomaly": t.is_anomaly,
        "new_balance": round(current_user.balance, 2),
    }


class PreferencesPayload(BaseModel):
    language: Optional[str] = Field(None, pattern="^(en|hi)$")
    theme: Optional[str] = Field(None, pattern="^(light|dark)$")
    monthly_budget: Optional[float] = Field(None, gt=0)
    full_name: Optional[str] = None


@router.post("/preferences")
def update_preferences(
    payload: PreferencesPayload,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
):
    """Save language, theme and budget preferences."""
    if payload.language:
        current_user.language = payload.language
    if payload.theme:
        current_user.theme = payload.theme
    if payload.monthly_budget:
        current_user.monthly_budget = payload.monthly_budget
    if payload.full_name is not None:
        current_user.full_name = payload.full_name
    db.commit()
    return {"status": "updated", "language": current_user.language, "theme": current_user.theme}


# ---------------------------------------------------------------------------
# AI Chat (Groq, grounded in real data)
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str
    lang: str = "en"
    context: Optional[dict] = None


@router.post("/chat")
def user_ai_chat(
    req: ChatRequest,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
    merchant: Merchant = Depends(get_current_merchant),
):
    """Groq-powered assistant with the user's real metrics and isolated history."""
    lang = req.lang or current_user.language or "en"

    # History *before* this turn
    history_rows = db.query(ChatMessage).filter(
        ChatMessage.user_id == current_user.id
    ).order_by(ChatMessage.created_at.desc()).limit(10).all()
    history = [
        {"sender": row.sender, "message": row.message}
        for row in reversed(history_rows)
    ]

    txns_data = _transaction_rows(db, current_user.id)
    analysis = analyze_user_finances(txns_data, monthly_budget=current_user.monthly_budget)
    financial_context = _build_chat_context(db, current_user, merchant, analysis, txns_data)

    result = ask_groq_assistant_ex(
        req.message,
        lang=lang,
        financial_context=financial_context,
        history=history,
    )
    reply = result["reply"]

    db.add(ChatMessage(
        id=f"msg_{uuid.uuid4().hex[:10]}",
        user_id=current_user.id,
        merchant_id=merchant.id,
        sender="user",
        message=req.message,
    ))
    db.add(ChatMessage(
        id=f"msg_{uuid.uuid4().hex[:10]}",
        user_id=current_user.id,
        merchant_id=merchant.id,
        sender="ai",
        message=reply,
    ))
    db.commit()

    return {
        "reply": reply,
        "lang": lang,
        "source": result.get("source", "offline"),
        "model": result.get("model"),
    }


# ---------------------------------------------------------------------------
# ML endpoints
# ---------------------------------------------------------------------------

@ml_router.get("/status")
def ml_status(db: Session = Depends(get_db)):
    """Current state of the trained models + size of the training corpus."""
    status_data = get_model_status()
    try:
        db_samples = db.query(MLTrainingSample).count()
        by_category = dict(
            db.query(MLTrainingSample.category, func.count(MLTrainingSample.id))
            .group_by(MLTrainingSample.category)
            .all()
        )
    except Exception:
        db_samples, by_category = 0, {}
    status_data["db_sample_count"] = db_samples
    status_data["db_samples_by_category"] = by_category
    return status_data


@ml_router.post("/train")
def train_ml_models(db: Session = Depends(get_db)):
    """Retrain all models from the curated corpus + database samples."""
    return train_from_db(db)


@ml_router.post("/train/bootstrap")
def train_ml_bootstrap():
    """Retrain from the built-in curated corpus only."""
    return train_models()


class TrainingSamplePayload(BaseModel):
    description: str = Field(..., min_length=2, max_length=255)
    category: str = Field(..., min_length=2, max_length=60)
    amount: float = Field(default=0.0, ge=0)


@ml_router.get("/samples")
def list_training_samples(
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """Browse the training corpus stored in the database."""
    rows = db.query(MLTrainingSample).order_by(
        MLTrainingSample.id.desc()
    ).limit(max(1, min(limit, 500))).all()
    return [
        {
            "id": r.id,
            "description": r.description,
            "category": r.category,
            "amount": r.amount,
            "source": r.source,
        }
        for r in rows
    ]


@ml_router.post("/samples")
def add_training_sample(
    payload: TrainingSamplePayload,
    db: Session = Depends(get_db),
):
    """Add a labelled example — it is used by the next /api/ml/train call."""
    existing = db.query(MLTrainingSample).filter(
        func.lower(MLTrainingSample.description) == payload.description.strip().lower()
    ).first()
    if existing:
        existing.category = payload.category.strip()
        existing.amount = payload.amount
        existing.source = "merchant"
        db.commit()
        return {"status": "updated", "id": existing.id}

    row = MLTrainingSample(
        description=payload.description.strip(),
        category=payload.category.strip(),
        amount=payload.amount,
        source="merchant",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"status": "created", "id": row.id}


class CategorizeRequest(BaseModel):
    description: str


@ml_router.post("/categorize")
def ml_categorize(req: CategorizeRequest):
    """Predict a transaction category with the NLP model."""
    cat = categorize_expense(req.description)
    return {"description": req.description, "category": cat}


class SpendingPredictRequest(BaseModel):
    daily_amounts: Optional[list[float]] = None


@ml_router.post("/predict-spending")
def ml_predict_spending(req: SpendingPredictRequest):
    """Predict 7-day and 30-day spending with the Ridge regressor."""
    return predict_future_spending(req.daily_amounts)
