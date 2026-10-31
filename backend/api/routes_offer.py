"""Offer creation, experiment results, chat, and product catalogue with user isolation."""
from __future__ import annotations
import uuid
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.orm import Session
from db.session import get_db
from db.models import Recommendation, Offer, Experiment, Merchant, Product, UserProfile, ChatMessage, SalesDaily
from core.auth import get_current_merchant, get_current_user
from engine.experiment import create_simulated_experiment, get_experiment_result
from ai.groq_client import ask_groq_assistant

offer_router = APIRouter(prefix="/api/offer", tags=["offer"])
experiment_router = APIRouter(prefix="/api/experiments", tags=["experiments"])
chat_router = APIRouter(prefix="/api/chat", tags=["chat"])
products_router = APIRouter(prefix="/api/products", tags=["products"])


def create_offer_for_merchant(rec_id: str, merchant: Merchant, db: Session) -> dict:
    """Internal helper to create an offer and experiment for a merchant."""
    rec = db.query(Recommendation).filter(
        Recommendation.id == rec_id,
        Recommendation.merchant_id == merchant.id,
    ).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    if rec.status not in ("approved", "modified"):
        raise HTTPException(status_code=400, detail="Recommendation must be approved or modified first")

    lang = merchant.language if merchant else "hi"
    actual_offer = rec.modified_offer_json or rec.offer_json or {}

    try:
        from ai.interfaces import ai_make_offer_copy
        copy_json = ai_make_offer_copy(actual_offer, lang)
    except Exception:
        copy_json = {"whatsapp": "Aaj ka special offer!", "headline": "SPECIAL OFFER", "cta": "Abhi Lo"}

    risk = rec.risk_json or {}
    units_cap = risk.get("units_cap", 40)
    valid_from = date.today()
    valid_to = valid_from + timedelta(days=7)

    offer = Offer(
        id="off_" + str(uuid.uuid4())[:8],
        recommendation_id=rec_id,
        merchant_id=merchant.id,
        copy_json=copy_json,
        poster_json={
            "headline": copy_json.get("headline", "SPECIAL OFFER"),
            "body": copy_json.get("whatsapp", ""),
            "cta": copy_json.get("cta", "Visit Now"),
            "qr_placeholder": True,
            "disclaimer": "[Simulated poster for promotional use]",
        },
        valid_from=valid_from,
        valid_to=valid_to,
        units_cap=units_cap,
        is_active=True,
    )
    db.add(offer)
    db.commit()
    db.refresh(offer)

    # Auto-create simulated experiment for merchant's products
    prods = db.query(Product).filter(
        Product.merchant_id == merchant.id,
        Product.is_active == True,
    ).all()
    t_ids = [p.id for p in prods[:2]]
    c_ids = [p.id for p in prods[2:4]]
    sell_price = actual_offer.get("original_price") or actual_offer.get("bundle_price") or 50
    cost_price = prods[0].cost_price if prods and prods[0].cost_price else sell_price * 0.7
    discount = actual_offer.get("discount_pct", 10)

    experiment = create_simulated_experiment(
        db, offer.id, merchant.id, t_ids, c_ids,
        cost_per_unit=cost_price,
        sell_price=sell_price,
        discount_pct=discount,
    )

    return {
        "offer_id": offer.id,
        "copy": copy_json,
        "poster": offer.poster_json,
        "valid_from": str(valid_from),
        "valid_to": str(valid_to),
        "units_cap": units_cap,
        "experiment_id": experiment.id,
        "data_label": "synthetic",
    }


# ─── Offer ──────────────────────────────────────────────────────────────────

@offer_router.post("/{rec_id}/create")
def create_offer(
    rec_id: str,
    db: Session = Depends(get_db),
    merchant: Merchant = Depends(get_current_merchant),
):
    """Create offer from an approved/modified recommendation owned by the current merchant."""
    return create_offer_for_merchant(rec_id, merchant, db)


@offer_router.get("")
def list_offers(
    db: Session = Depends(get_db),
    merchant: Merchant = Depends(get_current_merchant),
):
    """List offers strictly scoped to the authenticated merchant."""
    offers = db.query(Offer).filter(
        Offer.merchant_id == merchant.id
    ).order_by(Offer.created_at.desc()).all()
    return [
        {
            "id": o.id,
            "recommendation_id": o.recommendation_id,
            "copy": o.copy_json,
            "poster": o.poster_json,
            "valid_from": str(o.valid_from),
            "valid_to": str(o.valid_to),
            "units_cap": o.units_cap,
            "units_redeemed": o.units_redeemed,
            "is_active": o.is_active,
        }
        for o in offers
    ]


# ─── Experiments ─────────────────────────────────────────────────────────────

@experiment_router.get("/{exp_id}/result")
def experiment_result(
    exp_id: str,
    db: Session = Depends(get_db),
    merchant: Merchant = Depends(get_current_merchant),
):
    """Get experiment result with ownership check."""
    exp = db.query(Experiment).filter(
        Experiment.id == exp_id,
        Experiment.merchant_id == merchant.id,
    ).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return get_experiment_result(db, exp_id)


@experiment_router.get("")
def list_experiments(
    db: Session = Depends(get_db),
    merchant: Merchant = Depends(get_current_merchant),
):
    """List experiments strictly scoped to the authenticated merchant."""
    exps = db.query(Experiment).filter(
        Experiment.merchant_id == merchant.id
    ).order_by(Experiment.created_at.desc()).all()
    return [
        {
            "id": e.id,
            "offer_id": e.offer_id,
            "net_lift_pct": e.net_lift_pct,
            "gp_change_inr": e.gp_change_inr,
            "is_simulated": e.is_simulated,
            "data_label": e.data_label,
        }
        for e in exps
    ]


# ─── Chat ────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    lang: str = "hi"


@chat_router.get("/history")
def get_chat_history(
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
):
    """Retrieve isolated chat history for the authenticated user."""
    history = db.query(ChatMessage).filter(
        ChatMessage.user_id == current_user.id
    ).order_by(ChatMessage.created_at.asc()).limit(50).all()
    return [
        {
            "id": h.id,
            "sender": h.sender,
            "text": h.message,
            "time": h.created_at.strftime("%I:%M %p"),
        }
        for h in history
    ]


@chat_router.post("")
def chat(
    req: ChatRequest,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
    merchant: Merchant = Depends(get_current_merchant),
):
    """
    AI Business Assistant grounded in the shopkeeper's real business metrics.
    Saves conversation history scoped strictly to the authenticated user.
    """
    lang = req.lang or merchant.language or "hi"

    # Save user message
    user_msg = ChatMessage(
        id=f"msg_{uuid.uuid4().hex[:10]}",
        user_id=current_user.id,
        merchant_id=merchant.id,
        sender="user",
        message=req.message,
    )
    db.add(user_msg)

    # Gather authenticated user's actual shop metrics (NEVER other shops' data)
    product_count = db.query(Product).filter(
        Product.merchant_id == merchant.id,
        Product.is_active == True,
    ).count()

    total_sales_rows = db.query(SalesDaily).filter(SalesDaily.merchant_id == merchant.id).all()
    total_revenue = sum(s.total_amount for s in total_sales_rows)
    has_sales_history = len(total_sales_rows) > 0

    from engine.analysis import get_primary_weak_day
    weak_day = get_primary_weak_day(db, merchant.id)

    shop_context = {
        "shop_name": merchant.name,
        "shop_type": merchant.shop_type,
        "product_count": product_count,
        "total_revenue": total_revenue,
        "has_sales_history": has_sales_history,
        "weak_day": weak_day.get("weekday") if weak_day else None,
        "weak_dip": weak_day.get("dip_pct") if weak_day else None,
        "min_margin": merchant.min_margin_pct,
        "balance": current_user.balance,
    }

    try:
        reply = ask_groq_assistant(req.message, lang=lang, financial_context=shop_context)
    except Exception:
        if not has_sales_history and product_count == 0:
            reply = (
                "Namaste! Aapki dukaan abhi nayi hai aur koi sales ya product record nahi hai. "
                "Pehle Products tab mein jaakar apne products add karein taaki hum aapke liye behtareen offers bana sakein."
                if lang == "hi" else
                "Hello! Your store is newly registered with no sales or products recorded yet. "
                "Please add your inventory in the Products tab first so we can analyze your profits and suggest smart offers."
            )
        else:
            from ai.interfaces import ai_chat
            reply = ai_chat(req.message, lang, shop_context)

    # Save AI response
    ai_msg = ChatMessage(
        id=f"msg_{uuid.uuid4().hex[:10]}",
        user_id=current_user.id,
        merchant_id=merchant.id,
        sender="ai",
        message=reply,
    )
    db.add(ai_msg)
    db.commit()

    return {"reply": reply, "lang": lang}


# ─── Products ────────────────────────────────────────────────────────────────

class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    category: str = Field(default="general", max_length=60)
    sell_price: float = Field(..., gt=0)
    cost_price: Optional[float] = Field(default=None, ge=0)
    cost_source: str = Field(default="manual", max_length=20)


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    category: Optional[str] = Field(default=None, max_length=60)
    sell_price: Optional[float] = Field(default=None, gt=0)
    cost_price: Optional[float] = Field(default=None, ge=0)
    cost_source: Optional[str] = Field(default=None, max_length=20)
    is_active: Optional[bool] = None


@products_router.get("")
def list_products(
    db: Session = Depends(get_db),
    merchant: Merchant = Depends(get_current_merchant),
):
    """List products strictly belonging to the authenticated merchant."""
    prods = db.query(Product).filter(
        Product.merchant_id == merchant.id,
        Product.is_active == True,
    ).all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "category": p.category,
            "sell_price": p.sell_price,
            "cost_price": p.cost_price,
            "cost_source": p.cost_source,
            "is_active": p.is_active,
            "margin_pct": round((p.sell_price - p.cost_price) / p.sell_price * 100, 1)
            if p.cost_price and p.sell_price else None,
        }
        for p in prods
    ]


@products_router.post("")
def create_product(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    merchant: Merchant = Depends(get_current_merchant),
):
    """Add a product to the authenticated merchant's catalog."""
    prod = Product(merchant_id=merchant.id, **payload.model_dump())
    db.add(prod)
    db.commit()
    db.refresh(prod)
    return {"id": prod.id, "name": prod.name, "status": "created"}


@products_router.put("/{product_id}")
def update_product(
    product_id: int,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
    merchant: Merchant = Depends(get_current_merchant),
):
    """Update a product with strict ownership verification."""
    prod = db.query(Product).filter(
        Product.id == product_id,
        Product.merchant_id == merchant.id,
    ).first()
    if not prod:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found or access denied",
        )
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(prod, field, value)
    db.commit()
    return {"id": prod.id, "status": "updated"}


@products_router.delete("/{product_id}")
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    merchant: Merchant = Depends(get_current_merchant),
):
    """Deactivate a product with strict ownership verification."""
    prod = db.query(Product).filter(
        Product.id == product_id,
        Product.merchant_id == merchant.id,
    ).first()
    if not prod:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found or access denied",
        )
    prod.is_active = False
    db.commit()
    return {"status": "deactivated"}
