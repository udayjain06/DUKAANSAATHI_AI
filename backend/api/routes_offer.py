"""Offer creation, experiment results, and chat routes."""
from __future__ import annotations
import uuid
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from db.session import get_db
from db.models import Recommendation, Offer, Experiment, Merchant
from engine.experiment import create_simulated_experiment, get_experiment_result

offer_router = APIRouter(prefix="/api/offer", tags=["offer"])
experiment_router = APIRouter(prefix="/api/experiments", tags=["experiments"])
chat_router = APIRouter(prefix="/api/chat", tags=["chat"])
products_router = APIRouter(prefix="/api/products", tags=["products"])

MERCHANT_ID = 1


# ─── Offer ──────────────────────────────────────────────────────────────────

@offer_router.post("/{rec_id}/create")
def create_offer(rec_id: str, db: Session = Depends(get_db)):
    """Create offer from an approved/modified recommendation."""
    rec = db.query(Recommendation).filter(Recommendation.id == rec_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    if rec.status not in ("approved", "modified"):
        raise HTTPException(status_code=400, detail="Recommendation must be approved or modified first")

    merchant = db.query(Merchant).filter(Merchant.id == MERCHANT_ID).first()
    lang = merchant.language if merchant else "hi"

    # Build offer copy
    actual_offer = rec.modified_offer_json or rec.offer_json
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
        merchant_id=MERCHANT_ID,
        copy_json=copy_json,
        poster_json={
            "headline": copy_json.get("headline", "SPECIAL OFFER"),
            "body": copy_json.get("whatsapp", ""),
            "cta": copy_json.get("cta", "Visit Now"),
            "qr_placeholder": True,
            "disclaimer": "[Simulated poster — for demo only]",
        },
        valid_from=valid_from,
        valid_to=valid_to,
        units_cap=units_cap,
        is_active=True,
    )
    db.add(offer)
    db.commit()
    db.refresh(offer)

    # Auto-create simulated experiment
    offer_data = actual_offer or {}
    prods = db.query(__import__("db.models", fromlist=["Product"]).Product).filter(
        __import__("db.models", fromlist=["Product"]).Product.merchant_id == MERCHANT_ID
    ).all()
    t_ids = [p.id for p in prods[:2]]
    c_ids = [p.id for p in prods[2:4]]
    sell_price = offer_data.get("original_price") or offer_data.get("bundle_price") or 50
    cost_price = prods[0].cost_price if prods and prods[0].cost_price else sell_price * 0.7
    discount = offer_data.get("discount_pct", 10)

    experiment = create_simulated_experiment(
        db, offer.id, MERCHANT_ID, t_ids, c_ids,
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


@offer_router.get("")
def list_offers(db: Session = Depends(get_db)):
    offers = db.query(Offer).filter(Offer.merchant_id == MERCHANT_ID).order_by(Offer.created_at.desc()).all()
    return [
        {
            "id": o.id, "recommendation_id": o.recommendation_id,
            "copy": o.copy_json, "poster": o.poster_json,
            "valid_from": str(o.valid_from), "valid_to": str(o.valid_to),
            "units_cap": o.units_cap, "units_redeemed": o.units_redeemed,
            "is_active": o.is_active,
        }
        for o in offers
    ]


# ─── Experiments ─────────────────────────────────────────────────────────────

@experiment_router.get("/{exp_id}/result")
def experiment_result(exp_id: str, db: Session = Depends(get_db)):
    """Get experiment result with net lift and GP change."""
    return get_experiment_result(db, exp_id)


@experiment_router.get("")
def list_experiments(db: Session = Depends(get_db)):
    exps = db.query(Experiment).filter(Experiment.merchant_id == MERCHANT_ID).all()
    return [
        {
            "id": e.id, "offer_id": e.offer_id,
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


@chat_router.post("")
def chat(req: ChatRequest, db: Session = Depends(get_db)):
    """Hindi/English chat with DukaanSaathi AI."""
    merchant = db.query(Merchant).filter(Merchant.id == MERCHANT_ID).first()
    lang = req.lang or (merchant.language if merchant else "hi")
    try:
        from ai.interfaces import ai_chat
        reply = ai_chat(req.message, lang)
    except Exception:
        reply = "Sorry, AI temporarily unavailable. Please try again." if lang == "en" else \
                "Maafi, AI abhi available nahi hai. Thodi der mein try karein."
    return {"reply": reply, "lang": lang}


# ─── Products ────────────────────────────────────────────────────────────────

from db.models import Product
from pydantic import BaseModel as BM


class ProductCreate(BM):
    name: str
    category: str = "general"
    sell_price: float
    cost_price: Optional[float] = None
    cost_source: str = "manual"


class ProductUpdate(BM):
    name: Optional[str] = None
    category: Optional[str] = None
    sell_price: Optional[float] = None
    cost_price: Optional[float] = None
    cost_source: Optional[str] = None
    is_active: Optional[bool] = None


@products_router.get("")
def list_products(db: Session = Depends(get_db)):
    prods = db.query(Product).filter(Product.merchant_id == MERCHANT_ID).all()
    return [
        {
            "id": p.id, "name": p.name, "category": p.category,
            "sell_price": p.sell_price, "cost_price": p.cost_price,
            "cost_source": p.cost_source, "is_active": p.is_active,
            "margin_pct": round((p.sell_price - p.cost_price) / p.sell_price * 100, 1)
            if p.cost_price and p.sell_price else None,
        }
        for p in prods
    ]


@products_router.post("")
def create_product(payload: ProductCreate, db: Session = Depends(get_db)):
    prod = Product(merchant_id=MERCHANT_ID, **payload.model_dump())
    db.add(prod)
    db.commit()
    db.refresh(prod)
    return {"id": prod.id, "name": prod.name, "status": "created"}


@products_router.put("/{product_id}")
def update_product(product_id: int, payload: ProductUpdate, db: Session = Depends(get_db)):
    prod = db.query(Product).filter(Product.id == product_id, Product.merchant_id == MERCHANT_ID).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(prod, field, value)
    db.commit()
    return {"id": prod.id, "status": "updated"}


@products_router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    prod = db.query(Product).filter(Product.id == product_id, Product.merchant_id == MERCHANT_ID).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found")
    prod.is_active = False
    db.commit()
    return {"status": "deactivated"}

