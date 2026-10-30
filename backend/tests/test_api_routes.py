"""
API Integration tests for DukaanSaathi AI endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_root_endpoint():
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["app"] == "DukaanSaathi AI"
    assert data["status"] == "running"


def test_merchant_profile_and_setup():
    # Get profile
    resp = client.get("/api/merchant/profile")
    assert resp.status_code == 200
    data = resp.json()
    assert "shop_type" in data
    assert "min_margin_pct" in data

    # Update setup
    setup_payload = {
        "name": "Audit Test Store",
        "shop_type": "kirana",
        "min_margin_pct": 16.0,
        "language": "hi",
        "phone": "9876543210",
        "risk_budget_inr": 500.0,
    }
    resp = client.post("/api/merchant/setup", json=setup_payload)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Audit Test Store"
    assert resp.json()["min_margin_pct"] == 16.0


def test_sales_summary_endpoint():
    resp = client.get("/api/sales/summary?weeks=8")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_revenue" in data
    assert "weekly" in data
    assert "weekday_avg" in data
    assert data["data_label"] == "synthetic"


def test_insights_weak_day_endpoint():
    resp = client.get("/api/insights/weak-day")
    assert resp.status_code == 200
    data = resp.json()
    assert "primary_weak_day" in data
    assert "all_weekdays" in data
    assert len(data["all_weekdays"]) > 0


def test_insights_dashboard_endpoint():
    resp = client.get("/api/insights/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert "sales" in data
    assert "weak_day" in data
    assert "products" in data
    assert "pending_recommendations" in data


def test_margin_check_api_valid():
    payload = {
        "sell_price": 100.0,
        "cost_price": 70.0,
        "discount_pct": 20.0,
        "min_margin_pct": 15.0,
    }
    resp = client.post("/api/margin/check", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "blocked"
    assert data["before_gp"] == 30.0
    assert data["after_gp"] == 10.0
    assert data["after_pct"] == 12.5


def test_margin_check_api_validation_error():
    payload = {
        "sell_price": -10.0,  # Invalid
        "cost_price": 70.0,
        "discount_pct": 20.0,
        "min_margin_pct": 15.0,
    }
    resp = client.post("/api/margin/check", json=payload)
    assert resp.status_code == 422


def test_products_crud_flow():
    # 1. Create product
    new_prod = {
        "name": "Integration Test Product",
        "category": "snacks",
        "sell_price": 50.0,
        "cost_price": 35.0,
        "cost_source": "manual",
    }
    resp = client.post("/api/products", json=new_prod)
    assert resp.status_code == 200
    prod_id = resp.json()["id"]

    # 2. List products
    resp = client.get("/api/products")
    assert resp.status_code == 200
    prods = resp.json()
    assert any(p["id"] == prod_id for p in prods)

    # 3. Update product
    update_payload = {"sell_price": 55.0}
    resp = client.put(f"/api/products/{prod_id}", json=update_payload)
    assert resp.status_code == 200

    # 4. Deactivate product
    resp = client.delete(f"/api/products/{prod_id}")
    assert resp.status_code == 200


def test_recommendation_generate_and_list():
    resp = client.post("/api/recommendation")
    assert resp.status_code == 200
    rec_data = resp.json()
    assert "id" in rec_data
    assert "margin" in rec_data
    rec_id = rec_data["id"]

    # List
    resp = client.get("/api/recommendation")
    assert resp.status_code == 200
    assert len(resp.json()) > 0

    # Decision approve
    resp = client.post(f"/api/recommendation/{rec_id}/decision", json={"decision": "approved"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"

    # Verify offer was auto-created
    resp = client.get("/api/offer")
    assert resp.status_code == 200
    offers = resp.json()
    assert any(o.get("recommendation_id") == rec_id for o in offers)


def test_chat_endpoint():
    resp = client.post("/api/chat", json={"message": "Monday offer batao", "lang": "hi"})
    assert resp.status_code == 200
    data = resp.json()
    assert "reply" in data
    assert len(data["reply"]) > 0


def test_payment_plans_endpoint():
    resp = client.get("/api/payment/plans")
    assert resp.status_code == 200
    data = resp.json()
    assert "plans" in data
    assert len(data["plans"]) == 3
    assert "configured" in data


def test_payment_initiate_without_credentials():
    # Should safely return 503 payment_not_configured
    resp = client.post("/api/payment/initiate", json={"plan": "monthly"})
    assert resp.status_code == 503
    assert resp.json()["error"] == "payment_not_configured"


def test_bills_confirm_endpoint():
    payload = {
        "items": [
            {
                "product_name": "Test Tea Pack 250g",
                "cost_price": 95.0,
                "quantity": 5.0,
                "unit": "pack",
                "bill_ref": "TEST-BILL-01",
            }
        ]
    }
    resp = client.post("/api/bills/confirm", json=payload)
    assert resp.status_code == 200
    assert resp.json()["count"] == 1
    assert "Test Tea Pack 250g" in resp.json()["saved"]
