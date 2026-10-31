"""Recommendation + Bills routes with user-level data isolation."""
from __future__ import annotations
import uuid
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.orm import Session
from db.session import get_db
from db.models import (
    Recommendation, BillItem, Bill, Product, Merchant, Offer, Transaction,
)
from core.auth import get_current_merchant
from engine.recommendation import build_recommendation, apply_decision, get_pending_recommendations
from engine.margin import check_margin
from engine.ml_engine import categorize_expense, is_anomaly

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

MAX_UPLOAD_SIZE = 15 * 1024 * 1024  # 15 MB
ALLOWED_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".pdf")

BILL_RESPONSE_HELP = (
    "Review the extracted items, fix any OCR mistakes, then confirm to update "
    "your product cost prices."
)


def _bill_to_dict(bill: Bill) -> dict:
    return {
        "id": bill.id,
        "bill_ref": bill.bill_ref,
        "file_name": bill.file_name,
        "file_type": bill.file_type,
        "file_size": bill.file_size,
        "engine": bill.ocr_engine,
        "confidence": bill.ocr_confidence,
        "item_count": bill.item_count,
        "total_amount": bill.total_amount,
        "status": bill.status,
        "created_at": str(bill.created_at),
    }


@bills_router.get("")
def list_bills(
    db: Session = Depends(get_db),
    merchant: Merchant = Depends(get_current_merchant),
):
    """Every confirmed bill item saved by this merchant."""
    items = db.query(BillItem).filter(
        BillItem.merchant_id == merchant.id
    ).order_by(BillItem.created_at.desc()).limit(300).all()
    return [
        {
            "id": b.id,
            "bill_id": b.bill_id,
            "bill_ref": b.bill_ref,
            "product_name": b.product_name,
            "cost_price": b.cost_price,
            "quantity": b.quantity,
            "unit": b.unit,
            "created_at": str(b.created_at),
        }
        for b in items
    ]


@bills_router.get("/history")
def bill_history(
    limit: int = 25,
    db: Session = Depends(get_db),
    merchant: Merchant = Depends(get_current_merchant),
):
    """List uploaded source bills (including raw OCR status)."""
    rows = db.query(Bill).filter(
        Bill.merchant_id == merchant.id
    ).order_by(Bill.created_at.desc()).limit(max(1, min(limit, 100))).all()
    return [_bill_to_dict(b) for b in rows]


@bills_router.get("/history/{bill_id}")
def bill_detail(
    bill_id: int,
    db: Session = Depends(get_db),
    merchant: Merchant = Depends(get_current_merchant),
):
    """Full details of one uploaded bill, including raw OCR text."""
    bill = db.query(Bill).filter(
        Bill.id == bill_id,
        Bill.merchant_id == merchant.id,
    ).first()
    if not bill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")

    items = db.query(BillItem).filter(BillItem.bill_id == bill.id).all()
    return {
        **_bill_to_dict(bill),
        "raw_text": bill.raw_text or "",
        "items": [
            {
                "id": i.id,
                "product_name": i.product_name,
                "cost_price": i.cost_price,
                "quantity": i.quantity,
                "unit": i.unit,
                "confirmed": i.confirmed,
            }
            for i in items
        ],
    }


@bills_router.post("/upload")
async def upload_bill(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    merchant: Merchant = Depends(get_current_merchant),
):
    """Upload a bill photo / PDF and extract line items with local OCR."""
    filename = (file.filename or "bill").strip()
    content_type = (file.content_type or "").lower()

    if content_type and not (
        content_type.startswith("image/")
        or content_type == "application/pdf"
        or content_type == "application/octet-stream"
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Please upload a JPG/PNG image or a PDF invoice.",
        )
    if not content_type and not filename.lower().endswith(ALLOWED_EXTENSIONS):
        raise HTTPException(
            status_code=400,
            detail="Unsupported file. Please upload a JPG/PNG image or a PDF invoice.",
        )

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(contents) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File too large. Maximum size is 15 MB.",
        )

    from ai.ocr import extract_bill

    try:
        result = extract_bill(contents, filename=filename, content_type=content_type)
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=500, detail=f"OCR failed: {exc}")

    items = result.get("items", [])
    total_amount = round(
        sum(float(item.get("amount") or item.get("cost_price") or 0) for item in items), 2
    )

    bill = Bill(
        merchant_id=merchant.id,
        bill_ref=f"BILL-{uuid.uuid4().hex[:6].upper()}",
        file_name=filename,
        file_type=content_type or "unknown",
        file_size=len(contents),
        ocr_engine=result.get("engine", "none"),
        ocr_confidence=result.get("confidence"),
        raw_text=result.get("raw_text", ""),
        item_count=len(items),
        total_amount=total_amount,
        status="extracted" if items else "failed",
    )
    db.add(bill)
    db.commit()
    db.refresh(bill)

    return {
        "bill_id": bill.id,
        "bill_ref": bill.bill_ref,
        "extracted_items": items,
        "count": len(items),
        "total_amount": total_amount,
        "raw_text": result.get("raw_text", "")[:8000],
        "engine": result.get("engine", "none"),
        "confidence": result.get("confidence", 0.0),
        "pages": result.get("pages", 1),
        "warnings": result.get("warnings", []),
        "ai_available": len(items) > 0,
        "message": (
            f"OCR extracted {len(items)} item(s) using {result.get('engine')}. {BILL_RESPONSE_HELP}"
            if items else
            "OCR finished but no line items were recognised. "
            "Add the wholesale items manually below or try a sharper photo."
        ),
    }


class BillConfirmItem(BaseModel):
    product_name: str = Field(..., min_length=1, max_length=120)
    cost_price: float = Field(..., gt=0)
    quantity: float = Field(default=1.0, gt=0)
    unit: str = Field(default="unit", max_length=20)
    bill_ref: Optional[str] = Field(default=None, max_length=60)
    amount: Optional[float] = Field(default=None, ge=0)


class BillConfirmPayload(BaseModel):
    items: list[BillConfirmItem]
    bill_id: Optional[int] = None
    bill_ref: Optional[str] = Field(default=None, max_length=60)
    create_expense: bool = False
    expense_date: Optional[str] = None


@bills_router.post("/confirm")
def confirm_bill(
    payload: BillConfirmPayload,
    db: Session = Depends(get_db),
    merchant: Merchant = Depends(get_current_merchant),
):
    """Save confirmed bill items as product costs for the authenticated merchant."""
    bill: Optional[Bill] = None
    if payload.bill_id:
        bill = db.query(Bill).filter(
            Bill.id == payload.bill_id,
            Bill.merchant_id == merchant.id,
        ).first()
        if not bill:
            raise HTTPException(status_code=404, detail="Uploaded bill not found")

    bill_ref = payload.bill_ref or (bill.bill_ref if bill else None) or \
        f"BILL-{uuid.uuid4().hex[:6].upper()}"

    saved: list[str] = []
    total_amount = 0.0

    for item in payload.items:
        line_amount = item.amount if item.amount else round(item.cost_price * item.quantity, 2)
        total_amount += line_amount

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
                sell_price=round(item.cost_price * 1.3, 2),  # default 30% markup
                cost_source="bill",
            )
            db.add(prod)

        db.add(BillItem(
            merchant_id=merchant.id,
            bill_id=bill.id if bill else None,
            product_name=item.product_name,
            cost_price=item.cost_price,
            quantity=item.quantity,
            unit=item.unit,
            bill_ref=item.bill_ref or bill_ref,
            confirmed=True,
        ))
        saved.append(item.product_name)

    total_amount = round(total_amount, 2)

    if bill:
        bill.status = "confirmed"
        bill.item_count = len(saved)
        bill.total_amount = total_amount
        bill.bill_ref = bill_ref

    expense_created = None
    if payload.create_expense and total_amount > 0:
        user_id = merchant.user_id
        if user_id:
            txn_date = date.today()
            if payload.expense_date:
                try:
                    from datetime import datetime as _dt
                    txn_date = _dt.strptime(payload.expense_date, "%Y-%m-%d").date()
                except ValueError:
                    pass
            description = f"Supplier bill {bill_ref} ({len(saved)} items)"
            txn = Transaction(
                id=f"tx_{uuid.uuid4().hex[:10]}",
                user_id=user_id,
                type="expense",
                category=categorize_expense(description),
                amount=total_amount,
                description=description,
                date=txn_date,
                is_anomaly=is_anomaly(total_amount),
            )
            db.add(txn)
            expense_created = {"id": txn.id, "amount": total_amount, "date": str(txn_date)}

    db.commit()

    return {
        "saved": saved,
        "count": len(saved),
        "bill_id": bill.id if bill else None,
        "bill_ref": bill_ref,
        "total_amount": total_amount,
        "expense_created": expense_created,
        "status": "ok",
    }



