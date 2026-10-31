"""
User Dashboard, ML Predictions & Transaction Routes.
Provides isolated, dynamic financial data per authenticated user.
"""
from __future__ import annotations
import uuid
from datetime import date, datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from db.session import get_db
from db.models import UserProfile, Transaction, Merchant, Product, SalesDaily, ChatMessage
from core.auth import get_current_user, get_current_merchant
from engine.ml_engine import (
    categorize_expense,
    is_anomaly,
    predict_future_spending,
    analyze_user_finances,
    train_models,
)
from ai.groq_client import ask_groq_assistant

router = APIRouter(prefix="/api/user", tags=["user_dashboard"])
ml_router = APIRouter(prefix="/api/ml", tags=["ml"])


@router.get("/dashboard")
def get_user_dashboard(
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
):
    """Retrieve dynamic user dashboard with balance, spending, categories and ML predictions."""
    # Fetch authenticated user's own transactions
    txns = db.query(Transaction).filter(
        Transaction.user_id == current_user.id
    ).order_by(Transaction.date.desc()).all()

    txns_data = [
        {
            "id": t.id,
            "type": t.type,
            "category": t.category,
            "amount": t.amount,
            "description": t.description,
            "date": str(t.date),
            "is_anomaly": t.is_anomaly,
        }
        for t in txns
    ]

    # Run ML financial analyzer
    analysis = analyze_user_finances(txns_data, monthly_budget=current_user.monthly_budget)

    # Calculate actual user balance
    total_income = sum(t["amount"] for t in txns_data if t["type"] == "income")
    total_expense = sum(t["amount"] for t in txns_data if t["type"] == "expense")
    computed_balance = current_user.balance if not txns_data and current_user.balance > 0 else (total_income - total_expense)

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
            "total_income": analysis["total_income"],
            "total_expense": analysis["total_expense"],
            "savings_rate_pct": analysis["savings_rate_pct"],
        },
        "financial_summary": {
            "total_income": analysis["total_income"],
            "total_expense": analysis["total_expense"],
            "net_savings": round(analysis["total_income"] - analysis["total_expense"], 2),
            "savings_rate_pct": analysis["savings_rate_pct"],
            "monthly_budget": current_user.monthly_budget,
            "budget_spent_pct": round(
                (analysis["total_expense"] / current_user.monthly_budget * 100), 1
            ) if current_user.monthly_budget > 0 else 0.0,
            "has_data": analysis.get("has_data", len(txns_data) > 0),
        },
        "ml_predictions": {
            "predicted_7day_spending": analysis["predictions"]["next_7_days_total"],
            "predicted_30day_spending": analysis["predictions"]["next_30_days_total"],
            "trend": "steady" if analysis.get("has_data") else "new",
            "confidence_score": analysis["predictions"]["confidence_pct"],
        },
        "categories": [
            {
                "category": c["category"],
                "total_amount": c["amount"],
                "amount": c["amount"],
                "pct": c["pct"],
            }
            for c in analysis["categories"]
        ],
        "predictions": analysis["predictions"],
        "anomaly_count": analysis["anomaly_count"],
        "anomalies_count": analysis["anomaly_count"],
        "insights": analysis["insights"],
        "recent_transactions": txns_data[:10],
    }


@router.get("/transactions")
def get_user_transactions(
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
):
    """Retrieve full transaction ledger for the authenticated user."""
    txns = db.query(Transaction).filter(
        Transaction.user_id == current_user.id
    ).order_by(Transaction.date.desc()).all()

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
        for t in txns
    ]


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
    """Add a new transaction with automatic ML category & anomaly detection."""
    # ML Auto-Categorization if not supplied
    category = payload.category
    if not category or category.strip().lower() == "auto":
        category = categorize_expense(payload.description)

    # ML Anomaly Detection
    anomaly_flag = is_anomaly(payload.amount)

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

    # Update profile balance
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
    """Save user language, theme, and budget preferences."""
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


# ============================================================================
# ML ENDPOINTS
# ============================================================================

@ml_router.post("/train")
def train_ml_models():
    """Trigger real scikit-learn model training and save joblib artifacts."""
    return train_models()


class CategorizeRequest(BaseModel):
    description: str


@ml_router.post("/categorize")
def ml_categorize(req: CategorizeRequest):
    """Predict category using trained LogisticRegression NLP pipeline."""
    cat = categorize_expense(req.description)
    return {"description": req.description, "category": cat}


class SpendingPredictRequest(BaseModel):
    daily_amounts: Optional[list[float]] = None


@ml_router.post("/predict-spending")
def ml_predict_spending(req: SpendingPredictRequest):
    """Predict 7-day and 30-day spending using trained Ridge Regressor."""
    return predict_future_spending(req.daily_amounts)


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
    """Groq-powered conversational assistant with actual user metrics and isolated history."""
    lang = req.lang or current_user.language or "en"

    # Save user message
    user_msg = ChatMessage(
        id=f"msg_{uuid.uuid4().hex[:10]}",
        user_id=current_user.id,
        merchant_id=merchant.id,
        sender="user",
        message=req.message,
    )
    db.add(user_msg)

    # Gather authenticated user's actual shop metrics
    product_count = db.query(Product).filter(
        Product.merchant_id == merchant.id,
        Product.is_active == True,
    ).count()

    sales_rows = db.query(SalesDaily).filter(SalesDaily.merchant_id == merchant.id).all()
    total_revenue = sum(s.total_amount for s in sales_rows)
    txns = db.query(Transaction).filter(Transaction.user_id == current_user.id).all()
    total_expenses = sum(t.amount for t in txns if t.type == "expense")

    financial_context = {
        "shop_name": merchant.name,
        "shop_type": merchant.shop_type,
        "balance": current_user.balance,
        "total_income": total_revenue,
        "total_expense": total_expenses,
        "product_count": product_count,
        "has_sales": len(sales_rows) > 0,
        "predicted_30_days": 0.0 if not txns else None,
    }

    reply = ask_groq_assistant(req.message, lang=lang, financial_context=financial_context)

    # Save AI message
    ai_msg = ChatMessage(
        id=f"msg_{uuid.uuid4().hex[:10]}",
        user_id=current_user.id,
        merchant_id=merchant.id,
        sender="ai",
        message=reply,
    )
    db.add(ai_msg)
    db.commit()

    return {"reply": reply, "lang": req.lang}
