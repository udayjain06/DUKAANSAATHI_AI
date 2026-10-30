"""
User Dashboard, ML Predictions & Transaction Routes.
Provides isolated, dynamic financial data per authenticated user.
"""
from __future__ import annotations
import uuid
from datetime import date, datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from db.session import get_db
from db.models import UserProfile, Transaction
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


def get_current_user_profile(
    db: Session,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_user_email: Optional[str] = Header(None, alias="X-User-Email"),
) -> UserProfile:
    """Get or auto-initialize user profile for data isolation."""
    user_id = x_user_id or "demo-user-001"
    email = x_user_email or f"{user_id}@paytm.demo"

    profile = db.query(UserProfile).filter(UserProfile.id == user_id).first()
    if not profile:
        profile = UserProfile(
            id=user_id,
            email=email,
            full_name="Paytm User" if user_id == "demo-user-001" else email.split("@")[0].title(),
            balance=28450.0,
            language="en",
            theme="dark",
            monthly_budget=30000.0,
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)

        # Seed initial transactions for the new user profile so dashboard is immediately dynamic
        initial_txns = [
            ("Swiggy Biryani Dinner", 420.0, "Food", "expense", 1),
            ("IndianOil Petrol Refill", 1500.0, "Travel", "expense", 2),
            ("Blinkit Weekly Groceries", 1240.0, "Groceries", "expense", 3),
            ("Electricity Board Bill", 1850.0, "Utilities", "expense", 5),
            ("Netflix Subscription", 649.0, "Entertainment", "expense", 7),
            ("Amazon Shopping T-Shirt", 890.0, "Shopping", "expense", 8),
            ("Monthly Salary Credit", 55000.0, "Salary", "income", 10),
            ("Zomato Pizza Party", 780.0, "Food", "expense", 12),
            ("Doctor Consultation Apollo", 600.0, "Healthcare", "expense", 14),
            ("High Value Jewellery Purchase", 18500.0, "Shopping", "expense", 15),
        ]
        today = date.today()
        for desc, amt, cat, typ, days_ago in initial_txns:
            t = Transaction(
                id=f"tx_{uuid.uuid4().hex[:10]}",
                user_id=user_id,
                type=typ,
                category=cat,
                amount=amt,
                description=desc,
                date=today - timedelta(days=days_ago),
                is_anomaly=is_anomaly(amt),
            )
            db.add(t)
        db.commit()

    return profile


@router.get("/dashboard")
def get_user_dashboard(
    db: Session = Depends(get_db),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_user_email: Optional[str] = Header(None, alias="X-User-Email"),
):
    """Retrieve dynamic user dashboard with balance, spending, categories and ML predictions."""
    profile = get_current_user_profile(db, x_user_id, x_user_email)

    # Fetch user's own transactions
    txns = db.query(Transaction).filter(
        Transaction.user_id == profile.id
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
    analysis = analyze_user_finances(txns_data, monthly_budget=profile.monthly_budget)

    # Monthly Trend (Past 4 months summary)
    today = date.today()
    months_trend = [
        {"month": (today - timedelta(days=90)).strftime("%b"), "income": 52000, "expense": 34500},
        {"month": (today - timedelta(days=60)).strftime("%b"), "income": 55000, "expense": 32800},
        {"month": (today - timedelta(days=30)).strftime("%b"), "income": 54000, "expense": 31200},
        {"month": today.strftime("%b"), "income": analysis["total_income"], "expense": analysis["total_expense"]},
    ]

    return {
        "user": {
            "id": profile.id,
            "email": profile.email,
            "full_name": profile.full_name,
            "balance": profile.balance,
            "language": profile.language,
            "theme": profile.theme,
            "monthly_budget": profile.monthly_budget,
        },
        "financials": {
            "balance": analysis["balance"] + profile.balance,
            "total_income": analysis["total_income"],
            "total_expense": analysis["total_expense"],
            "savings_rate_pct": analysis["savings_rate_pct"],
        },
        "categories": analysis["categories"],
        "monthly_trend": months_trend,
        "ml_predictions": analysis["predictions"],
        "insights": analysis["insights"],
        "anomalies_count": analysis["anomalies_count"],
        "recent_transactions": txns_data[:10],
    }


class NewTransactionPayload(BaseModel):
    description: str = Field(..., min_length=1)
    amount: float = Field(..., gt=0)
    type: str = Field(default="expense", pattern="^(income|expense)$")
    category: Optional[str] = None
    date: Optional[str] = None


@router.post("/transactions")
def add_transaction(
    payload: NewTransactionPayload,
    db: Session = Depends(get_db),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_user_email: Optional[str] = Header(None, alias="X-User-Email"),
):
    """Add a new transaction with automatic ML category & anomaly detection."""
    profile = get_current_user_profile(db, x_user_id, x_user_email)

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
        user_id=profile.id,
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
        profile.balance += payload.amount
    else:
        profile.balance -= payload.amount

    db.commit()
    db.refresh(t)

    return {
        "status": "success",
        "category": t.category,
        "is_anomaly": t.is_anomaly,
        "transaction": {
            "id": t.id,
            "description": t.description,
            "amount": t.amount,
            "category": t.category,
            "type": t.type,
            "date": str(t.date),
            "is_anomaly": t.is_anomaly,
        },
        "new_balance": profile.balance,
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
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_user_email: Optional[str] = Header(None, alias="X-User-Email"),
):
    """Save user language, theme, and budget preferences."""
    profile = get_current_user_profile(db, x_user_id, x_user_email)
    if payload.language:
        profile.language = payload.language
    if payload.theme:
        profile.theme = payload.theme
    if payload.monthly_budget:
        profile.monthly_budget = payload.monthly_budget
    if payload.full_name is not None:
        profile.full_name = payload.full_name
    db.commit()
    return {"status": "updated", "language": profile.language, "theme": profile.theme}


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
def user_ai_chat(req: ChatRequest):
    """Groq-powered conversational assistant for budgeting and predictions."""
    reply = ask_groq_assistant(req.message, lang=req.lang, financial_context=req.context)
    return {"reply": reply, "lang": req.lang}
