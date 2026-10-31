"""Recommendation + Bills routes with user-level data isolation."""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.orm import Session
from db.session import get_db
from db.models import Recommendation, BillItem, Product, Merchant, Offer
from core.auth import get_current_merchant
from engine.recommendation import build_recommendation, apply_decision, get_pending_recommendations
from engine.margin import check_margin

router = APIRouter(prefix="/api/recommendation", tags=["recommendation"])
bills_router = APIRouter(prefix="/api/bills", tags=["bills"])
margin_router = APIRouter(prefix="/api/margin", tags=["margin"])


# ─── Recommendation ─────────────────────────────────────────────────────────

@router.post("")
def create_recommendation(
    db: Session = Depends(get_db),
    merchant: Merchant = Depends(get_current_merchant),
):
    """Generate a new recommendation for the authenticated merchant."""
    lang = merchant.language if merchant else "hi"
    return build_recommendation(db, merchant.id, lang)


@router.get("")
def list_recommendations(
    db: Session = Depends(get_db),
    merchant: Merchant = Depends(get_current_merchant),
):
    """List recommendations strictly scoped to the authenticated merchant."""
    recs = db.query(Recommendation).filter(
        Recommendation.merchant_id == merchant.id
    ).order_by(Recommendation.created_at.desc()).limit(20).all()
    return [
        {
            "id": r.id, "weak_day": r.weak_day, "dip_pct": r.dip_pct,
            "offer": r.offer_json, "margin": r.margin_json,
            "risk": r.risk_json, "explanation": r.explanation_json,
            "status": r.status, "data_label": r.data_label,
            "created_at": str(r.created_at),
        }
        for r in recs
    ]


@router.get("/pending")
def pending_recommendations(
    db: Session = Depends(get_db),
    merchant: Merchant = Depends(get_current_merchant),
):
    """Get pending recommendations for the authenticated merchant."""
    return get_pending_recommendations(db, merchant.id)


@router.get("/{rec_id}")
def get_recommendation(
    rec_id: str,
    db: Session = Depends(get_db),
    merchant: Merchant = Depends(get_current_merchant),
):
    """Fetch recommendation by ID with strict ownership validation."""
    rec = db.query(Recommendation).filter(
        Recommendation.id == rec_id,
        Recommendation.merchant_id == merchant.id,
    ).first()
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found")
    return {
        "id": rec.id, "weak_day": rec.weak_day, "dip_pct": rec.dip_pct,
        "offer": rec.offer_json, "margin": rec.margin_json,
        "risk": rec.risk_json, "explanation": rec.explanation_json,
        "status": rec.status, "data_label": rec.data_label,
        "modified_offer": rec.modified_offer_json,
    }


class DecisionPayload(BaseModel):
    decision: str  # approved | modified | rejected
    modified_offer: Optional[dict] = None


@router.post("/{rec_id}/decision")
def decision(
    rec_id: str,
    payload: DecisionPayload,
    db: Session = Depends(get_db),
    merchant: Merchant = Depends(get_current_merchant),
):
    """Approve, Modify, or Reject a recommendation owned by the current merchant."""
    rec = db.query(Recommendation).filter(
        Recommendation.id == rec_id,
        Recommendation.merchant_id == merchant.id,
    ).first()
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found")

    result = apply_decision(db, rec_id, payload.decision, payload.modified_offer)
    if payload.decision in ("approved", "modified"):
        from api.routes_offer import create_offer_for_merchant
        existing_offer = db.query(Offer).filter(Offer.recommendation_id == rec_id).first()
        if not existing_offer:
            try:
                create_offer_for_merchant(rec_id, merchant, db)
            except Exception:
                pass
    return result


# ─── Margin Calculator ───────────────────────────────────────────────────────

class MarginCalcRequest(BaseModel):
    sell_price: float = Field(..., gt=0, description="Selling price must be > 0")
    cost_price: float = Field(..., ge=0, description="Cost price must be >= 0")
    discount_pct: float = Field(..., ge=0, le=100, description="Discount must be 0-100%")
    min_margin_pct: float = Field(default=15.0, ge=0, le=100)


@margin_router.post("/check")
def margin_check(req: MarginCalcRequest):
    """Run margin calculation directly against safety thresholds."""
    try:
        return check_margin(req.sell_price, req.cost_price, req.discount_pct, req.min_margin_pct)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


# ─── Bills ──────────────────────────────────────────────────────────────────

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB


@bills_router.get("")
def list_bills(
    db: Session = Depends(get_db),
    merchant: Merchant = Depends(get_current_merchant),
):
    """Retrieve all confirmed bills for the authenticated merchant."""
    items = db.query(BillItem).filter(
        BillItem.merchant_id == merchant.id
    ).order_by(BillItem.created_at.desc()).all()
    return [
        {
            "id": b.id,
            "bill_ref": b.bill_ref,
            "product_name": b.product_name,
            "cost_price": b.cost_price,
            "quantity": b.quantity,
            "unit": b.unit,
            "created_at": str(b.created_at),
        }
        for b in items
    ]


@bills_router.post("/upload")
async def upload_bill(
    file: UploadFile = File(...),
    merchant: Merchant = Depends(get_current_merchant),
):
    """Upload a bill photo — AI extracts items (falls back to empty list)."""
    allowed_types = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
    if file.content_type and file.content_type not in allowed_types and not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload an image or PDF invoice.")

    contents = await file.read()
    if len(contents) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 10 MB.")

    try:
        from ai.interfaces import ai_extract_bill_items
        items = ai_extract_bill_items(contents)
    except Exception:
        items = []
    return {
        "extracted_items": items,
        "count": len(items),
        "ai_available": len(items) > 0,
        "message": "Review and confirm items below." if items else
                   "AI extraction completed. Review or enter wholesale items manually below.",
    }


class BillConfirmItem(BaseModel):
    product_name: str = Field(..., min_length=1, max_length=120)
    cost_price: float = Field(..., gt=0)
    quantity: float = Field(default=1.0, gt=0)
    unit: str = Field(default="unit", max_length=20)
    bill_ref: Optional[str] = Field(default=None, max_length=60)


class BillConfirmPayload(BaseModel):
    items: list[BillConfirmItem]


@bills_router.post("/confirm")
def confirm_bill(
    payload: BillConfirmPayload,
    db: Session = Depends(get_db),
    merchant: Merchant = Depends(get_current_merchant),
):
    """Save confirmed bill items as product costs strictly for the authenticated merchant."""
    saved = []
    for item in payload.items:
        # Update or create product under this merchant
        prod = db.query(Product).filter(
            Product.merchant_id == merchant.id,
            Product.name == item.product_name,
        ).first()
        if prod:
            prod.cost_price = item.cost_price
            prod.cost_source = "bill"
        else:
            prod = Product(
                merchant_id=merchant.id,
                name=item.product_name,
                cost_price=item.cost_price,
                sell_price=round(item.cost_price * 1.3, 2),  # Default 30% markup
                cost_source="bill",
            )
            db.add(prod)

        bi = BillItem(
            merchant_id=merchant.id,
            product_name=item.product_name,
            cost_price=item.cost_price,
            quantity=item.quantity,
            unit=item.unit,
            bill_ref=item.bill_ref,
            confirmed=True,
        )
        db.add(bi)
        saved.append(item.product_name)

    db.commit()
    return {"saved": saved, "count": len(saved), "status": "ok"}
