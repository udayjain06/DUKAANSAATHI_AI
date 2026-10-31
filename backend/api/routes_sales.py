"""Sales summary, insights, and recording routes with user-level isolation."""
from __future__ import annotations
from datetime import date
from fastapi import APIRouter, Depends, Query, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from db.session import get_db
from db.models import Merchant, SalesDaily, SalesProductDaily, Product
from core.auth import get_current_merchant
from engine.analysis import (
    get_sales_summary,
    detect_weak_days,
    get_primary_weak_day,
    get_product_insights,
)

router = APIRouter(prefix="/api/sales", tags=["sales"])
insights_router = APIRouter(prefix="/api/insights", tags=["insights"])

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


class RecordSaleRequest(BaseModel):
    sale_date: date = Field(default_factory=date.today)
    total_amount: float = Field(..., gt=0)
    txn_count: int = Field(default=1, ge=1)
    product_sales: list[dict] = Field(default_factory=list)  # list of {product_id, units, revenue}


@router.get("/summary")
def sales_summary(
    weeks: int = Query(default=8, ge=1, le=52),
    db: Session = Depends(get_db),
    merchant: Merchant = Depends(get_current_merchant),
):
    """Sales summary scoped strictly to the authenticated user's shop."""
    return get_sales_summary(db, merchant.id, weeks)


@router.post("/record")
def record_daily_sale(
    payload: RecordSaleRequest,
    db: Session = Depends(get_db),
    merchant: Merchant = Depends(get_current_merchant),
):
    """Record a real daily sales figure for the authenticated merchant."""
    weekday_str = WEEKDAYS[payload.sale_date.weekday()]

    # Check for existing record on this day
    existing = db.query(SalesDaily).filter(
        SalesDaily.merchant_id == merchant.id,
        SalesDaily.date == payload.sale_date,
    ).first()

    if existing:
        existing.total_amount += payload.total_amount
        existing.txn_count += payload.txn_count
        existing.is_synthetic = False
        sale_entry = existing
    else:
        sale_entry = SalesDaily(
            merchant_id=merchant.id,
            date=payload.sale_date,
            weekday=weekday_str,
            total_amount=payload.total_amount,
            txn_count=payload.txn_count,
            is_synthetic=False,
        )
        db.add(sale_entry)

    # Optional product sales breakdown
    for ps in payload.product_sales:
        pid = ps.get("product_id")
        units = ps.get("units", 1)
        rev = ps.get("revenue", 0.0)
        # Validate product belongs to this merchant
        prod = db.query(Product).filter(Product.id == pid, Product.merchant_id == merchant.id).first()
        if prod:
            db.add(SalesProductDaily(
                merchant_id=merchant.id,
                date=payload.sale_date,
                product_id=prod.id,
                units=units,
                revenue=rev,
                is_synthetic=False,
            ))

    db.commit()
    db.refresh(sale_entry)
    return {"status": "recorded", "id": sale_entry.id, "date": str(sale_entry.date), "total_amount": sale_entry.total_amount}


@insights_router.get("/weak-day")
def weak_day(
    db: Session = Depends(get_db),
    merchant: Merchant = Depends(get_current_merchant),
):
    """Detect weak sales days scoped to the authenticated merchant."""
    days = detect_weak_days(db, merchant.id)
    primary = get_primary_weak_day(db, merchant.id)
    sales = get_sales_summary(db, merchant.id)
    return {
        "primary_weak_day": primary,
        "all_weekdays": days,
        "data_label": sales.get("data_label", "synthetic"),
        "has_data": len(days) > 0,
        "note": "Based on consistent historical pattern, not statistical significance.",
    }


@insights_router.get("/products")
def product_insights(
    weeks: int = Query(default=8, ge=1, le=52),
    db: Session = Depends(get_db),
    merchant: Merchant = Depends(get_current_merchant),
):
    """Top and low performing products for the authenticated merchant."""
    return get_product_insights(db, merchant.id, weeks)


@insights_router.get("/dashboard")
def dashboard_summary(
    db: Session = Depends(get_db),
    merchant: Merchant = Depends(get_current_merchant),
):
    """Combined dashboard data strictly isolated to the authenticated user's shop."""
    sales = get_sales_summary(db, merchant.id)
    weak = get_primary_weak_day(db, merchant.id)
    products = get_product_insights(db, merchant.id)

    from db.models import Recommendation, Offer
    pending_recs = db.query(Recommendation).filter(
        Recommendation.merchant_id == merchant.id,
        Recommendation.status == "pending",
    ).count()

    active_offers = db.query(Offer).filter(
        Offer.merchant_id == merchant.id,
        Offer.is_active == True,
    ).count()

    has_sales = bool(float(sales.get("total_revenue", 0)) > 0)

    return {
        "sales": sales,
        "weak_day": weak,
        "products": products,
        "pending_recommendations": pending_recs,
        "active_offers": active_offers,
        "has_sales": has_sales,
        "data_label": str(sales.get("data_label", "synthetic")),
    }
