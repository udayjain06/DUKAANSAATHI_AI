import pytest
from fastapi.testclient import TestClient
from main import app
from db.session import init_db
from engine.ml_engine import categorize_expense, is_anomaly, predict_future_spending

from core.security import create_access_token
from db.session import SessionLocal
from db.models import UserProfile

# Ensure SQLite schema is created for test tables
init_db()
client = TestClient(app)

# Ensure test-user-42 exists
_db = SessionLocal()
try:
    if not _db.query(UserProfile).filter(UserProfile.id == "test-user-42").first():
        _db.add(UserProfile(id="test-user-42", email="testuser@paytm.test", full_name="Test User 42"))
        _db.commit()
finally:
    _db.close()

test_token = create_access_token({"sub": "test-user-42", "email": "testuser@paytm.test"})
auth_headers = {"Authorization": f"Bearer {test_token}"}

def test_ml_categorize_logic():
    assert categorize_expense("Dominos Farmhouse Pizza") == "Food"
    assert categorize_expense("IndianOil Diesel Fuel Refill") == "Travel"
    assert categorize_expense("Apollo Pharmacy Medicine Tablets") == "Healthcare"
    assert categorize_expense("Electricity Power Bill payment") == "Utilities"

def test_ml_anomaly_detection():
    # Normal spending
    assert is_anomaly(350.0) is False
    assert is_anomaly(1200.0) is False
    # Large unusual purchase
    assert is_anomaly(65000.0) is True

def test_ml_future_spending_prediction():
    pred = predict_future_spending([500.0, 750.0, 600.0, 900.0, 450.0, 800.0, 650.0])
    assert "next_7_days_total" in pred
    assert "next_30_days_total" in pred
    assert pred["next_7_days_total"] > 0
    assert pred["next_30_days_total"] > pred["next_7_days_total"]

def test_user_dashboard_endpoint():
    response = client.get("/api/user/dashboard", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "financials" in data
    assert "ml_predictions" in data
    assert "categories" in data
    assert "recent_transactions" in data
    assert data["user"]["id"] == "test-user-42"

def test_add_transaction_with_auto_ml_categorization():
    payload = {
        "description": "Starbucks Cappuccino Coffee",
        "amount": 320.0,
        "type": "expense",
        "category": "auto"
    }
    response = client.post("/api/user/transactions", json=payload, headers=auth_headers)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["category"] == "Food"
    assert res_data["is_anomaly"] is False

def test_ml_api_endpoints():
    cat_res = client.post("/api/ml/categorize", json={"description": "Indigo flight ticket"})
    assert cat_res.status_code == 200
    assert cat_res.json()["category"] == "Travel"

    pred_res = client.post("/api/ml/predict-spending", json={"daily_amounts": [1000, 1200, 1100, 1300]})
    assert pred_res.status_code == 200
    assert pred_res.json()["next_7_days_total"] > 0
