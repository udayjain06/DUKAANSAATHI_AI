"""Sales summary and weak-day insight routes."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from db.session import get_db
from engine.analysis import get_sales_summary, detect_weak_days, get_primary_weak_day, get_product_insights

router = APIRouter(prefix="/api/sales", tags=["sales"])
insights_router = APIRouter(prefix="/api/insights", tags=["insights"])

MERCHANT_ID = 1


@router.get("/summary")
def sales_summary(weeks: int = Query(default=8, ge=1, le=52), db: Session = Depends(get_db)):
    """8-week sales summary with weekday averages and best/worst day."""
    return get_sales_summary(db, MERCHANT_ID, weeks)


@insights_router.get("/weak-day")
def weak_day(db: Session = Depends(get_db)):
    """Detect weak sales days with dip%, confidence, consistency."""
    days = detect_weak_days(db, MERCHANT_ID)
    primary = get_primary_weak_day(db, MERCHANT_ID)
    return {
        "primary_weak_day": primary,
        "all_weekdays": days,
        "data_label": "synthetic",
        "note": "Based on consistent historical pattern, not statistical significance.",
    }


@insights_router.get("/products")
def product_insights(weeks: int = Query(default=8, ge=1, le=52), db: Session = Depends(get_db)):
    """Top and low performing products."""
    return get_product_insights(db, MERCHANT_ID, weeks)


@insights_router.get("/dashboard")
def dashboard_summary(db: Session = Depends(get_db)):
    """Combined dashboard data: sales + weak day + product insights."""
    sales = get_sales_summary(db, MERCHANT_ID)
    weak = get_primary_weak_day(db, MERCHANT_ID)
    products = get_product_insights(db, MERCHANT_ID)
    from db.models import Recommendation, Offer
    pending_recs = db.query(Recommendation).filter(
        Recommendation.merchant_id == MERCHANT_ID,
        Recommendation.status == "pending",
    ).count()
    active_offers = db.query(Offer).filter(
        Offer.merchant_id == MERCHANT_ID,
        Offer.is_active == True,
    ).count()
    return {
        "sales": sales,
        "weak_day": weak,
        "products": products,
        "pending_recommendations": pending_recs,
        "active_offers": active_offers,
        "data_label": "synthetic",
    }

