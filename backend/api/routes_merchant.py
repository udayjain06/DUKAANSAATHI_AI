"""Merchant setup routes with user-level workspace isolation."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from db.session import get_db
from db.models import Merchant
from core.auth import get_current_merchant

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
def merchant_setup(
    payload: MerchantSetup,
    db: Session = Depends(get_db),
    merchant: Merchant = Depends(get_current_merchant),
):
    """Update the merchant profile for the authenticated user's shop."""
    merchant.shop_type = payload.shop_type
    merchant.min_margin_pct = payload.min_margin_pct
    merchant.language = payload.language
    merchant.name = payload.name
    merchant.phone = payload.phone
    merchant.risk_budget_inr = payload.risk_budget_inr
    db.commit()
    db.refresh(merchant)
    return merchant


@router.get("/profile", response_model=MerchantResponse)
def get_profile(merchant: Merchant = Depends(get_current_merchant)):
    """Retrieve merchant profile for the authenticated user."""
    return merchant
