"""Paytm Payment Gateway integration (official checksum library)."""
from __future__ import annotations
import json
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.session import get_db
from db.models import PaymentOrder, Merchant
from core.auth import get_current_merchant

try:
    from paytmchecksum import PaytmChecksum
except Exception:  # pragma: no cover - dependency guard
    PaytmChecksum = None

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

PENDING_ORDER_TTL_MINUTES = 30


def _paytm_configured() -> bool:
    return bool(
        PaytmChecksum
        and PAYTM_MID
        and PAYTM_KEY
        and PAYTM_MID != "YOUR_MID"
        and PAYTM_KEY != "YOUR_KEY"
    )


def _generate_checksum(params: dict, key: str) -> str:
    """Generate an official Paytm checksum (SHA256 + AES via paytmchecksum)."""
    if not PaytmChecksum or not key:
        return ""
    return PaytmChecksum.generateSignature({k: str(v) for k, v in params.items()}, key)


def _verify_checksum(params: dict, key: str, checksum: str) -> bool:
    """Verify an official Paytm checksum from a callback (form or JSON)."""
    if not PaytmChecksum or not key or not checksum:
        return False
    clean = {k: v for k, v in params.items() if k != "CHECKSUMHASH"}
    try:
        if PaytmChecksum.verifySignature(clean, key, checksum):
            return True
        compact = json.dumps(clean, separators=(",", ":"))
        return bool(PaytmChecksum.verifySignature(compact, key, checksum))
    except Exception:
        return False


def _verify_transaction_with_paytm(order_id: str) -> dict:
    """Server-side order status enquiry against Paytm."""
    if not _paytm_configured():
        return {}
    import requests

    body = {"mid": PAYTM_MID, "orderId": order_id}
    signature = PaytmChecksum.generateSignature(json.dumps(body), PAYTM_KEY)
    payload = {"body": body, "head": {"signature": signature}}

    try:
        resp = requests.post(
            PAYTM_VERIFY_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.error("Paytm status enquiry failed: %s", exc)
        return {}


def _result_status(response: dict) -> str:
    body = response.get("body") or {}
    return str(
        body.get("resultInfo", {}).get("resultStatus")
        or body.get("resultStatus")
        or ""
    )


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
                    "Set PAYTM_MID and PAYTM_MERCHANT_KEY in your .env file."
                ),
                "required_env_vars": ["PAYTM_MID", "PAYTM_MERCHANT_KEY"],
            },
        )

    plan = PLANS.get(payload.plan)
    if not plan:
        raise HTTPException(status_code=400, detail=f"Invalid plan. Choose from: {list(PLANS)}")

    amount = plan["amount"]
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=PENDING_ORDER_TTL_MINUTES)
    existing = (
        db.query(PaymentOrder)
        .filter(
            PaymentOrder.merchant_id == merchant.id,
            PaymentOrder.status == "PENDING",
            PaymentOrder.plan_name == payload.plan,
            PaymentOrder.created_at >= cutoff,
        )
        .first()
    )

    if existing:
        order_id = existing.order_id
    else:
        order_id = f"DS_{uuid.uuid4().hex[:12].upper()}"
        db.add(
            PaymentOrder(
                merchant_id=merchant.id,
                order_id=order_id,
                amount=amount,
                plan_name=payload.plan,
                status="PENDING",
            )
        )
        db.commit()

    params = {
        "MID": PAYTM_MID,
        "WEBSITE": PAYTM_WEBSITE,
        "ORDER_ID": order_id,
        "TXN_AMOUNT": f"{amount:.2f}",
        "CUST_ID": f"merchant_{merchant.id}",
        "CALLBACK_URL": PAYTM_CALLBACK_URL,
        "CHANNEL_ID": os.getenv("PAYTM_CHANNEL_ID", "WEB"),
        "INDUSTRY_TYPE_ID": "Retail",
    }
    params["CHECKSUMHASH"] = _generate_checksum(params, PAYTM_KEY)

    return {
        "order_id": order_id,
        "amount": amount,
        "plan": plan["label"],
        "paytm_params": params,
        "txn_url": PAYTM_TXN_URL,
        "env": PAYTM_ENV,
    }


async def _read_callback_params(request: Request) -> tuple[dict, str]:
    """Return callback fields and checksum for form, query, or JSON callbacks."""
    if request.method.upper() == "GET":
        params = dict(request.query_params)
        return params, params.get("CHECKSUMHASH", "")

    content_type = (request.headers.get("content-type") or "").lower()
    if content_type.startswith("application/json"):
        data = await request.json()
        if isinstance(data, dict) and isinstance(data.get("body"), dict):
            body = dict(data["body"])
            signature = str((data.get("head") or {}).get("signature", ""))
            return body, signature
        if isinstance(data, dict):
            return dict(data), str(data.get("CHECKSUMHASH", ""))
        return {}, ""

    form = await request.form()
    params = {k: str(v) for k, v in form.items()}
    return params, params.get("CHECKSUMHASH", "")


@router.api_route("/callback", methods=["GET", "POST"])
async def payment_callback(request: Request, db: Session = Depends(get_db)):
    """Paytm callback: verify the checksum before updating any order state."""
    params, checksum = await _read_callback_params(request)
    params.pop("CHECKSUMHASH", None)

    if not _verify_checksum(params, PAYTM_KEY, checksum):
        logger.warning("Paytm callback checksum mismatch")
        return JSONResponse(status_code=400, content={"error": "invalid_checksum"})

    order_id = str(params.get("ORDERID") or params.get("orderId") or "")
    if not order_id:
        return JSONResponse(status_code=400, content={"error": "missing_order_id"})

    po = db.query(PaymentOrder).filter(PaymentOrder.order_id == order_id).first()
    if not po:
        return JSONResponse(status_code=404, content={"error": "order_not_found"})
    if po.status == "SUCCESS":
        return {"status": "already_processed", "order_id": order_id}

    verify_response = _verify_transaction_with_paytm(order_id)
    verified_status = _result_status(verify_response)

    if verified_status == "TXN_SUCCESS":
        po.status = "SUCCESS"
    elif verified_status in ("TXN_FAILURE", "CANCELLED"):
        po.status = verified_status
    else:
        po.status = "PENDING"

    po.txn_id = str(params.get("TXNID") or params.get("txnId") or "")
    po.paytm_response_json = params
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
    """Return the locally verified payment status."""
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
    return {
        "plans": [
            {"id": k, "name": v["label"], "amount": v["amount"], "currency": "INR"}
            for k, v in PLANS.items()
        ],
        "configured": _paytm_configured(),
        "env": PAYTM_ENV,
    }
