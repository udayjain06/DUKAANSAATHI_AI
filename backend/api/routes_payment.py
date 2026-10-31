"""Paytm Payment Gateway integration."""
from __future__ import annotations
import os
import uuid
import json
import hashlib
import hmac
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from db.session import get_db
from db.models import PaymentOrder, Merchant
from core.auth import get_current_merchant, get_optional_user

router = APIRouter(prefix="/api/payment", tags=["payment"])
logger = logging.getLogger(__name__)

PAYTM_MID = os.getenv("PAYTM_MID", "")
PAYTM_KEY = os.getenv("PAYTM_MERCHANT_KEY", "")
PAYTM_ENV = os.getenv("PAYTM_ENV", "staging")
PAYTM_WEBSITE = os.getenv("PAYTM_WEBSITE", "WEBSTAGING")
PAYTM_CALLBACK_URL = os.getenv("PAYTM_CALLBACK_URL", "http://localhost:8000/api/payment/callback")

PAYTM_TXN_URL = (
    "https://securegw-stage.paytm.in/theia/processTransaction"
    if PAYTM_ENV == "staging"
    else "https://securegw.paytm.in/theia/processTransaction"
)

PAYTM_VERIFY_URL = (
    "https://securegw-stage.paytm.in/v3/order/status"
    if PAYTM_ENV == "staging"
    else "https://securegw.paytm.in/v3/order/status"
)

PLANS = {
    "monthly": {"amount": 299.00, "label": "Monthly Plan"},
    "quarterly": {"amount": 799.00, "label": "Quarterly Plan"},
    "annual": {"amount": 2499.00, "label": "Annual Plan"},
}

MERCHANT_ID = 1


def _paytm_configured() -> bool:
    return bool(PAYTM_MID and PAYTM_KEY and
                PAYTM_MID != "YOUR_MID" and PAYTM_KEY != "YOUR_KEY")


def _generate_checksum(params: dict, key: str) -> str:
    """Generate Paytm checksum using HMAC-SHA256."""
    if not key:
        return ""
    sorted_params = {k: str(v) for k, v in sorted(params.items())}
    param_string = "|".join(sorted_params.values())
    signature = hmac.new(key.encode(), param_string.encode(), hashlib.sha256).hexdigest()
    return signature


def _verify_checksum(params: dict, key: str, checksum: str) -> bool:
    """Verify Paytm checksum from callback."""
    if not key or not checksum:
        return False
    params_copy = {k: v for k, v in params.items() if k != "CHECKSUMHASH"}
    expected = _generate_checksum(params_copy, key)
    return hmac.compare_digest(expected, checksum)


def _verify_transaction_with_paytm(order_id: str) -> dict:
    """Server-side transaction status verification from Paytm."""
    import requests as req_lib
    body = {
        "body": {"mid": PAYTM_MID, "orderId": order_id},
    }
    # Build signature for verify call
    body_str = json.dumps(body["body"], separators=(",", ":"))
    checksum = _generate_checksum({"body": body_str}, PAYTM_KEY)
    body["head"] = {"signature": checksum}

    try:
        resp = req_lib.post(PAYTM_VERIFY_URL, json=body, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error(f"Paytm verify error: {e}")
        return {}


class InitPaymentRequest(BaseModel):
    plan: str = "monthly"


@router.post("/initiate")
def initiate_payment(
    payload: InitPaymentRequest,
    db: Session = Depends(get_db),
    merchant: Merchant = Depends(get_current_merchant),
):
    """Create a Paytm payment order for the authenticated merchant."""
    if not _paytm_configured():
        return JSONResponse(
            status_code=503,
            content={
                "error": "payment_not_configured",
                "message": (
                    "Paytm credentials are not configured. "
                    "Set PAYTM_MID and PAYTM_MERCHANT_KEY in your .env file. "
                    "Get credentials from https://business.paytm.com/"
                ),
                "required_env_vars": ["PAYTM_MID", "PAYTM_MERCHANT_KEY"],
            },
        )

    plan = PLANS.get(payload.plan)
    if not plan:
        raise HTTPException(status_code=400, detail=f"Invalid plan. Choose from: {list(PLANS)}")

    order_id = f"DS_{uuid.uuid4().hex[:12].upper()}"
    amount = plan["amount"]

    # Check idempotency: don't create duplicate pending orders
    existing = db.query(PaymentOrder).filter(
        PaymentOrder.merchant_id == merchant.id,
        PaymentOrder.status == "PENDING",
        PaymentOrder.plan_name == payload.plan,
    ).first()
    if existing:
        order_id = existing.order_id
    else:
        po = PaymentOrder(
            merchant_id=merchant.id,
            order_id=order_id,
            amount=amount,
            plan_name=payload.plan,
            status="PENDING",
        )
        db.add(po)
        db.commit()

    params = {
        "MID": PAYTM_MID,
        "WEBSITE": PAYTM_WEBSITE,
        "ORDER_ID": order_id,
        "TXN_AMOUNT": str(amount),
        "CUST_ID": f"merchant_{MERCHANT_ID}",
        "CALLBACK_URL": PAYTM_CALLBACK_URL,
        "CHANNEL_ID": os.getenv("PAYTM_CHANNEL_ID", "WEB"),
        "INDUSTRY_TYPE_ID": "Retail",
    }
    checksum = _generate_checksum(params, PAYTM_KEY)
    params["CHECKSUMHASH"] = checksum

    return {
        "order_id": order_id,
        "amount": amount,
        "plan": plan["label"],
        "paytm_params": params,
        "txn_url": PAYTM_TXN_URL,
        "env": PAYTM_ENV,
    }


@router.post("/callback")
async def payment_callback(request: Request, db: Session = Depends(get_db)):
    """Paytm server-to-server callback. Verifies authenticity before updating status."""
    form = await request.form()
    params = dict(form)

    checksum = params.pop("CHECKSUMHASH", "")
    if not _verify_checksum(params, PAYTM_KEY, checksum):
        logger.warning("Paytm callback checksum mismatch")
        return JSONResponse(status_code=400, content={"error": "invalid_checksum"})

    order_id = params.get("ORDERID", "")
    txn_status = params.get("STATUS", "")
    txn_id = params.get("TXNID", "")

    # Server-side verification — never trust browser/callback alone
    verify_resp = _verify_transaction_with_paytm(order_id)
    verified_status = verify_resp.get("body", {}).get("resultInfo", {}).get("resultStatus", "")

    po = db.query(PaymentOrder).filter(PaymentOrder.order_id == order_id).first()
    if not po:
        return JSONResponse(status_code=404, content={"error": "order_not_found"})

    if po.status == "SUCCESS":
        # Idempotent: already processed
        return {"status": "already_processed"}

    if verified_status == "TXN_SUCCESS":
        po.status = "SUCCESS"
    elif verified_status in ("TXN_FAILURE", "CANCELLED"):
        po.status = verified_status
    else:
        po.status = "PENDING"

    po.txn_id = txn_id
    po.paytm_response_json = dict(params)
    po.verified_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()

    return {"status": po.status, "order_id": order_id}


@router.get("/orders")
def list_merchant_orders(
    db: Session = Depends(get_db),
    merchant: Merchant = Depends(get_current_merchant),
):
    """List payment orders strictly for the authenticated merchant."""
    orders = db.query(PaymentOrder).filter(
        PaymentOrder.merchant_id == merchant.id
    ).order_by(PaymentOrder.created_at.desc()).all()
    return [
        {
            "order_id": po.order_id,
            "amount": po.amount,
            "plan": po.plan_name,
            "status": po.status,
            "txn_id": po.txn_id,
            "created_at": str(po.created_at),
            "verified_at": str(po.verified_at) if po.verified_at else None,
        }
        for po in orders
    ]


@router.get("/status/{order_id}")
def payment_status(order_id: str, db: Session = Depends(get_db)):
    """Query payment status from DB (post-verification)."""
    po = db.query(PaymentOrder).filter(PaymentOrder.order_id == order_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Order not found")
    return {
        "order_id": po.order_id,
        "amount": po.amount,
        "plan": po.plan_name,
        "status": po.status,
        "txn_id": po.txn_id,
        "created_at": str(po.created_at),
        "verified_at": str(po.verified_at) if po.verified_at else None,
    }


@router.get("/plans")
def get_plans():
    """Return available subscription plans."""
    return {
        "plans": [
            {"id": k, "name": v["label"], "amount": v["amount"], "currency": "INR"}
            for k, v in PLANS.items()
        ],
        "configured": _paytm_configured(),
        "env": PAYTM_ENV,
    }

