"""Merchant setup routes."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from db.session import get_db
from db.models import Merchant

router = APIRouter(prefix="/api/merchant", tags=["merchant"])


class MerchantSetup(BaseModel):
    shop_type: str = Field(default="kirana", pattern="^(kirana|bakery)$")
    min_margin_pct: float = Field(default=15.0, ge=0, le=80)
    language: str = Field(default="hi", pattern="^(hi|en)$")
    name: str = Field(default="My Shop", max_length=120)
    phone: str = Field(default="", max_length=20)
    risk_budget_inr: float = Field(default=400.0, ge=0)


class MerchantResponse(BaseModel):
    id: int
    name: str
    shop_type: str
    min_margin_pct: float
    language: str
    risk_budget_inr: float
    phone: str | None

    model_config = {"from_attributes": True}


@router.post("/setup", response_model=MerchantResponse)
def merchant_setup(payload: MerchantSetup, db: Session = Depends(get_db)):
    """Create or update merchant profile (merchant_id=1 for demo)."""
    merchant = db.query(Merchant).filter(Merchant.id == 1).first()
    if merchant:
        merchant.shop_type = payload.shop_type
        merchant.min_margin_pct = payload.min_margin_pct
        merchant.language = payload.language
        merchant.name = payload.name
        merchant.phone = payload.phone
        merchant.risk_budget_inr = payload.risk_budget_inr
    else:
        merchant = Merchant(
            id=1,
            shop_type=payload.shop_type,
            min_margin_pct=payload.min_margin_pct,
            language=payload.language,
            name=payload.name,
            phone=payload.phone,
            risk_budget_inr=payload.risk_budget_inr,
        )
        db.add(merchant)
    db.commit()
    db.refresh(merchant)
    return merchant


@router.get("/profile", response_model=MerchantResponse)
def get_profile(db: Session = Depends(get_db)):
    merchant = db.query(Merchant).filter(Merchant.id == 1).first()
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not set up yet")
    return merchant

