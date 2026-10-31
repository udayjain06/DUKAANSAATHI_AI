"""
DukaanSaathi AI — Authentication Routes.
Provides signup, login, session validation (me), demo login, and logout.
Enforces secure password hashing and JWT token issuance.
"""
from __future__ import annotations
import uuid
import re
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from db.session import get_db
from db.models import UserProfile, Merchant
from core.security import hash_password, verify_password, create_access_token
from core.auth import get_current_user, get_current_merchant

router = APIRouter(tags=["auth"])

EMAIL_REGEX = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class SignUpRequest(BaseModel):
    email: str = Field(..., description="Valid email address")
    password: str = Field(..., min_length=6, description="Password at least 6 characters")
    full_name: Optional[str] = Field(default="", max_length=120)
    shop_name: Optional[str] = Field(default="", max_length=120)
    shop_type: Optional[str] = Field(default="kirana", pattern="^(kirana|bakery)$")


class LoginRequest(BaseModel):
    email: str
    password: str


class UserSummary(BaseModel):
    id: str
    email: str
    full_name: str
    is_demo: bool
    balance: float
    language: str
    theme: str


class MerchantSummary(BaseModel):
    id: int
    name: str
    shop_type: str
    min_margin_pct: float
    risk_budget_inr: float
    language: str
    phone: Optional[str] = None


class AuthResponse(BaseModel):
    status: str = "success"
    token: str
    token_type: str = "bearer"
    user: UserSummary
    merchant: MerchantSummary


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: SignUpRequest, db: Session = Depends(get_db)):
    """
    Register a new shopkeeper account with a completely fresh, empty workspace.
    Passwords are securely hashed using PBKDF2-HMAC-SHA256.
    """
    clean_email = payload.email.strip().lower()
    if not re.match(EMAIL_REGEX, clean_email):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Please provide a valid email address.",
        )

    # Check for existing user
    existing_user = db.query(UserProfile).filter(UserProfile.email == clean_email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists. Please log in.",
        )

    user_id = f"usr_{uuid.uuid4().hex[:12]}"
    pwd_hash = hash_password(payload.password)

    # Fresh account: zero initial balance, zero transactions, non-demo
    user = UserProfile(
        id=user_id,
        email=clean_email,
        password_hash=pwd_hash,
        full_name=payload.full_name.strip() if payload.full_name else "",
        balance=0.0,
        monthly_budget=30000.0,
        language="hi",
        theme="dark",
        is_demo=False,
    )
    db.add(user)
    db.flush()

    shop_title = (
        payload.shop_name.strip()
        if payload.shop_name and payload.shop_name.strip()
        else (f"{payload.full_name.strip()}'s Shop" if payload.full_name else "My Shop")
    )

    merchant = Merchant(
        user_id=user.id,
        name=shop_title,
        shop_type=payload.shop_type or "kirana",
        min_margin_pct=15.0,
        language="hi",
        risk_budget_inr=400.0,
        phone=None,
    )
    db.add(merchant)
    db.commit()
    db.refresh(user)
    db.refresh(merchant)

    token = create_access_token({"sub": user.id, "email": user.email})

    return {
        "status": "success",
        "token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "is_demo": user.is_demo,
            "balance": user.balance,
            "language": user.language,
            "theme": user.theme,
        },
        "merchant": {
            "id": merchant.id,
            "name": merchant.name,
            "shop_type": merchant.shop_type,
            "min_margin_pct": merchant.min_margin_pct,
            "risk_budget_inr": merchant.risk_budget_inr,
            "language": merchant.language,
            "phone": merchant.phone,
        },
    }


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate shopkeeper by validating credentials against stored password hash.
    Returns signed JWT access token.
    """
    clean_email = payload.email.strip().lower()
    user = db.query(UserProfile).filter(UserProfile.email == clean_email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check password hash or allow standard demo password for demo accounts
    is_valid = False
    if user.password_hash and verify_password(payload.password, user.password_hash):
        is_valid = True
    elif (user.is_demo or user.email == "demo@dukaansaathi.ai") and payload.password in ("Demo@123", "demo", "demo123"):
        is_valid = True
        if not user.password_hash:
            user.password_hash = hash_password("Demo@123")
            db.commit()

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Retrieve or initialize linked merchant workspace
    merchant = db.query(Merchant).filter(Merchant.user_id == user.id).first()
    if not merchant:
        merchant = Merchant(
            user_id=user.id,
            name=f"{user.full_name or 'My'} Shop",
            shop_type="kirana",
            min_margin_pct=15.0,
            language=user.language or "hi",
            risk_budget_inr=400.0,
        )
        db.add(merchant)
        db.commit()
        db.refresh(merchant)

    token = create_access_token({"sub": user.id, "email": user.email})

    return {
        "status": "success",
        "token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "is_demo": user.is_demo,
            "balance": user.balance,
            "language": user.language,
            "theme": user.theme,
        },
        "merchant": {
            "id": merchant.id,
            "name": merchant.name,
            "shop_type": merchant.shop_type,
            "min_margin_pct": merchant.min_margin_pct,
            "risk_budget_inr": merchant.risk_budget_inr,
            "language": merchant.language,
            "phone": merchant.phone,
        },
    }


@router.post("/demo", response_model=AuthResponse)
def demo_login(db: Session = Depends(get_db)):
    """
    Access the dedicated Demo Environment.
    Links directly to the sample 8-week sales and product dataset for demonstrations.
    """
    # Find existing demo account by ID, email, or is_demo flag to avoid duplicate constraints
    demo_user = (
        db.query(UserProfile)
        .filter(
            (UserProfile.id == "demo-user-001") |
            (UserProfile.email == "demo@dukaansaathi.ai") |
            (UserProfile.is_demo == True)
        )
        .first()
    )
    if not demo_user:
        demo_user = UserProfile(
            id="demo-user-001",
            email="demo@dukaansaathi.ai",
            password_hash=hash_password("Demo@123"),
            full_name="Demo Shopkeeper",
            balance=28450.0,
            monthly_budget=30000.0,
            language="hi",
            theme="dark",
            is_demo=True,
        )
        db.add(demo_user)
        db.commit()
        db.refresh(demo_user)
    else:
        # Ensure demo user has proper demo flag & password hash
        updated = False
        if not demo_user.is_demo:
            demo_user.is_demo = True
            updated = True
        if not demo_user.password_hash:
            demo_user.password_hash = hash_password("Demo@123")
            updated = True
        if updated:
            db.commit()
            db.refresh(demo_user)

    merchant = db.query(Merchant).filter(Merchant.id == 1).first()
    if not merchant:
        merchant = db.query(Merchant).filter(Merchant.user_id == demo_user.id).first()
    if not merchant:
        from engine.seed import run_seed
        run_seed(db, shop_type="kirana")
        merchant = db.query(Merchant).filter(Merchant.id == 1).first()
        if not merchant:
            merchant = db.query(Merchant).first()

    if merchant and merchant.user_id != demo_user.id:
        merchant.user_id = demo_user.id
        db.commit()
        db.refresh(merchant)

    token = create_access_token({"sub": demo_user.id, "email": demo_user.email})

    return {
        "status": "success",
        "token": token,
        "token_type": "bearer",
        "user": {
            "id": demo_user.id,
            "email": demo_user.email,
            "full_name": demo_user.full_name,
            "is_demo": True,
            "balance": demo_user.balance,
            "language": demo_user.language,
            "theme": demo_user.theme,
        },
        "merchant": {
            "id": merchant.id if merchant else 1,
            "name": merchant.name if merchant else "Sharma General Store",
            "shop_type": merchant.shop_type if merchant else "kirana",
            "min_margin_pct": merchant.min_margin_pct if merchant else 15.0,
            "risk_budget_inr": merchant.risk_budget_inr if merchant else 400.0,
            "language": merchant.language if merchant else "hi",
            "phone": merchant.phone if merchant else None,
        },
    }


@router.get("/me")
def get_current_user_info(
    current_user: UserProfile = Depends(get_current_user),
    current_merchant: Merchant = Depends(get_current_merchant),
):
    """Validate current session token and return user & merchant profile details."""
    return {
        "status": "authenticated",
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "is_demo": current_user.is_demo,
            "balance": current_user.balance,
            "language": current_user.language,
            "theme": current_user.theme,
            "monthly_budget": current_user.monthly_budget,
            "created_at": str(current_user.created_at),
        },
        "merchant": {
            "id": current_merchant.id,
            "name": current_merchant.name,
            "shop_type": current_merchant.shop_type,
            "min_margin_pct": current_merchant.min_margin_pct,
            "risk_budget_inr": current_merchant.risk_budget_inr,
            "language": current_merchant.language,
            "phone": current_merchant.phone,
        },
    }


@router.post("/logout")
def logout():
    """Client logout confirmation."""
    return {"status": "logged_out", "message": "Session terminated successfully."}

