"""Regression tests for balance accounting, upload validation and API errors."""
import io
import os
import sys

from fastapi.testclient import TestClient
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from main import app

client = TestClient(app)


def _png_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (4, 4), "white").save(buffer, format="PNG")
    return buffer.getvalue()


def _auth_headers(email: str) -> dict:
    payload = {
        "email": email,
        "password": "Password123!",
        "full_name": "Audit User",
        "shop_name": "Audit Store",
        "shop_type": "kirana",
    }
    response = client.post("/api/auth/signup", json=payload)
    if response.status_code == 409:
        response = client.post(
            "/api/auth/login",
            json={"email": email, "password": payload["password"]},
        )
    assert response.status_code in (200, 201), response.text
    return {"Authorization": f"Bearer {response.json()['token']}"}


def test_balance_updates_exactly_once():
    headers = _auth_headers("balance-audit@example.com")
    before = client.get("/api/user/dashboard", headers=headers).json()["financials"]["balance"]

    response = client.post(
        "/api/user/transactions",
        headers=headers,
        json={"description": "Audit coffee", "amount": 100.0, "type": "expense"},
    )
    assert response.status_code == 200

    after = client.get("/api/user/dashboard", headers=headers).json()["financials"]["balance"]
    assert round(before - after, 2) == 100.0


def test_bill_upload_rejects_invalid_file_type():
    headers = _auth_headers("bill-audit@example.com")
    response = client.post(
        "/api/bills/upload",
        headers=headers,
        files={"file": ("bill.txt", b"not a bill", "text/plain")},
    )
    assert response.status_code == 400


def test_bill_upload_handles_fake_image_gracefully():
    headers = _auth_headers("bill-audit@example.com")
    response = client.post(
        "/api/bills/upload",
        headers=headers,
        files={"file": ("bill.png", b"not-an-image", "image/png")},
    )
    assert response.status_code == 200
    assert response.json()["extracted_items"] == []


def test_bill_upload_accepts_valid_image_without_ai_key():
    headers = _auth_headers("bill-audit@example.com")
    response = client.post(
        "/api/bills/upload",
        headers=headers,
        files={"file": ("bill.png", _png_bytes(), "image/png")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["extracted_items"] == []
    assert data["ai_available"] is False
    assert data["message"]


def test_decision_returns_404_for_missing_recommendation():
    headers = _auth_headers("decision-audit@example.com")
    response = client.post(
        "/api/recommendation/rec_missing/decision",
        headers=headers,
        json={"decision": "approved"},
    )
    assert response.status_code == 404


def test_decision_rejects_invalid_value():
    headers = _auth_headers("decision-audit@example.com")
    client.post(
        "/api/products",
        headers=headers,
        json={
            "name": "Audit Product",
            "category": "grocery",
            "sell_price": 100.0,
            "cost_price": 70.0,
        },
    )
    created = client.post("/api/recommendation", headers=headers).json()
    response = client.post(
        f"/api/recommendation/{created['id']}/decision",
        headers=headers,
        json={"decision": "banana"},
    )
    assert response.status_code == 400
