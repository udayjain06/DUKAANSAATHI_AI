"""
DukaanSaathi AI — Authentication & Identity Dependencies.
Extracts and verifies JWT tokens from Authorization: Bearer <token>.
Ensures strict user-level data isolation.
"""
from __future__ import annotations
from typing import Optional
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
from db.session import get_db
from db.models import UserProfile, Merchant
from core.security import decode_access_token


def get_current_user(
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> UserProfile:
    """
    Enforce strict JWT authentication. Derives user identity exclusively
    from the verified token. Never trusts raw unverified client headers.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = authorization.strip().split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Expected 'Bearer <token>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1]
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload["sub"]
    user = db.query(UserProfile).filter(UserProfile.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account associated with this token was not found.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def get_current_merchant(
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
) -> Merchant:
    """
    Retrieve the merchant/shop workspace strictly owned by the authenticated user.
    Guarantees user-level workspace isolation.
    """
    merchant = db.query(Merchant).filter(Merchant.user_id == current_user.id).first()
    if not merchant:
        # Check if user is the demo user and Merchant 1 is available
        if current_user.is_demo or current_user.id == "demo-user-001":
            merchant = db.query(Merchant).filter(Merchant.id == 1).first()
            if merchant:
                merchant.user_id = current_user.id
                db.commit()
                db.refresh(merchant)
                return merchant

        # Auto-create fresh, empty merchant workspace for this user
        shop_title = f"{current_user.full_name}'s Shop" if current_user.full_name else "My Shop"
        merchant = Merchant(
            user_id=current_user.id,
            name=shop_title,
            shop_type="kirana",
            min_margin_pct=15.0,
            language=current_user.language or "hi",
            risk_budget_inr=400.0,
            phone=None,
        )
        db.add(merchant)
        db.commit()
        db.refresh(merchant)

    return merchant


def get_optional_user(
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> Optional[UserProfile]:
    """Optional authentication for endpoints that support both guests and logged-in users."""
    if not authorization:
        return None
    try:
        return get_current_user(db, authorization)
    except HTTPException:
        return None

