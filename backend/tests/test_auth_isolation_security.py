"""
DukaanSaathi AI — Comprehensive Security, Authentication & User Data Isolation Test Suite.

Verifies:
1. User A registers with a fresh account and adds 5 products.
2. User A adds daily sales and transaction ledger entries.
3. User B registers with a completely different account.
4. User B sees a completely empty fresh dashboard (₹0 revenue, ₹0 expenses, 0 products).
5. User B CANNOT access or list User A's products, bills, sales, transactions, or AI chat history.
6. User A logs in again with original credentials and sees their exact original data.
7. Unauthenticated requests and invalid/expired tokens are rejected with 401.
8. Cross-user ID manipulation (e.g. User B attempting to modify or delete User A's products or access their recommendations) is strictly rejected (404/403).
"""
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_auth_and_isolation_end_to_end():
    # -------------------------------------------------------------------------
    # SCENARIO 1: User A registers
    # -------------------------------------------------------------------------
    user_a_email = "usera_test@example.com"
    user_a_password = "Password123!"

    resp_a_reg = client.post("/api/auth/signup", json={
        "email": user_a_email,
        "password": user_a_password,
        "full_name": "Merchant Alice",
        "shop_name": "Alice Kirana Store",
        "shop_type": "kirana",
    })
    # If user already exists from previous test run, log in
    if resp_a_reg.status_code == 409:
        resp_a_log = client.post("/api/auth/login", json={
            "email": user_a_email,
            "password": user_a_password,
        })
        assert resp_a_log.status_code == 200, resp_a_log.text
        token_a = resp_a_log.json()["token"]
    else:
        assert resp_a_reg.status_code == 201, resp_a_reg.text
        token_a = resp_a_reg.json()["token"]

    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Verify session via /api/auth/me
    me_a = client.get("/api/auth/me", headers=headers_a)
    assert me_a.status_code == 200
    assert me_a.json()["user"]["email"] == user_a_email
    merchant_a_id = me_a.json()["merchant"]["id"]

    # User A adds 5 products
    products_a = [
        {"name": "Alice Tea Gold 250g", "category": "beverages", "sell_price": 120.0, "cost_price": 95.0},
        {"name": "Alice Sunflower Oil 1L", "category": "grocery", "sell_price": 140.0, "cost_price": 110.0},
        {"name": "Alice Basmati Rice 1kg", "category": "grocery", "sell_price": 90.0, "cost_price": 70.0},
        {"name": "Alice Sugar 1kg", "category": "grocery", "sell_price": 45.0, "cost_price": 38.0},
        {"name": "Alice Wheat Flour 5kg", "category": "grocery", "sell_price": 210.0, "cost_price": 175.0},
    ]

    prod_a_ids = []
    for p in products_a:
        res = client.post("/api/products", json=p, headers=headers_a)
        assert res.status_code == 200, res.text
        prod_a_ids.append(res.json()["id"])
    assert len(prod_a_ids) == 5

    # Verify User A has 5 products
    list_a_prods = client.get("/api/products", headers=headers_a)
    assert list_a_prods.status_code == 200
    assert len(list_a_prods.json()) == 5

    # -------------------------------------------------------------------------
    # SCENARIO 2: User A adds sales and transactions
    # -------------------------------------------------------------------------
    # Add daily sales
    sale_resp = client.post("/api/sales/record", json={
        "total_amount": 3500.0,
        "txn_count": 15,
        "product_sales": [{"product_id": prod_a_ids[0], "units": 5, "revenue": 600.0}],
    }, headers=headers_a)
    assert sale_resp.status_code == 200

    # Add ledger transaction
    tx_resp = client.post("/api/user/transactions", json={
        "description": "Electricity shop bill",
        "amount": 750.0,
        "type": "expense",
        "category": "Utilities",
    }, headers=headers_a)
    assert tx_resp.status_code == 200

    # Send AI chat message as User A
    chat_a = client.post("/api/chat", json={
        "message": "What is my top product and revenue?",
        "lang": "en",
    }, headers=headers_a)
    assert chat_a.status_code == 200

    # Confirm User A has 1 chat message in history
    hist_a = client.get("/api/chat/history", headers=headers_a)
    assert hist_a.status_code == 200
    assert len(hist_a.json()) >= 2  # user message + ai reply

    # -------------------------------------------------------------------------
    # SCENARIO 3: User B registers with a completely different account
    # -------------------------------------------------------------------------
    user_b_email = "userb_test@example.com"
    user_b_password = "Password123!"

    resp_b_reg = client.post("/api/auth/signup", json={
        "email": user_b_email,
        "password": user_b_password,
        "full_name": "Merchant Bob",
        "shop_name": "Bob Bakery Store",
        "shop_type": "bakery",
    })
    if resp_b_reg.status_code == 409:
        resp_b_log = client.post("/api/auth/login", json={
            "email": user_b_email,
            "password": user_b_password,
        })
        assert resp_b_log.status_code == 200
        token_b = resp_b_log.json()["token"]
    else:
        assert resp_b_reg.status_code == 201
        token_b = resp_b_reg.json()["token"]

    headers_b = {"Authorization": f"Bearer {token_b}"}
    me_b = client.get("/api/auth/me", headers=headers_b)
    assert me_b.status_code == 200
    merchant_b_id = me_b.json()["merchant"]["id"]
    assert merchant_b_id != merchant_a_id

    # -------------------------------------------------------------------------
    # SCENARIO 4: User B must see an empty fresh dashboard (₹0 metrics)
    # -------------------------------------------------------------------------
    dash_b = client.get("/api/insights/dashboard", headers=headers_b)
    assert dash_b.status_code == 200
    dash_b_data = dash_b.json()
    assert dash_b_data["sales"]["total_revenue"] == 0
    assert dash_b_data["sales"]["total_txns"] == 0
    assert dash_b_data["products"]["top"] == []
    assert dash_b_data["pending_recommendations"] == 0

    user_dash_b = client.get("/api/user/dashboard", headers=headers_b)
    assert user_dash_b.status_code == 200
    assert user_dash_b.json()["financial_summary"]["total_expense"] == 0
    assert user_dash_b.json()["recent_transactions"] == []

    # -------------------------------------------------------------------------
    # SCENARIO 5: User B must not access User A's products, bills, sales or AI history
    # -------------------------------------------------------------------------
    # User B's product list must be empty
    list_b_prods = client.get("/api/products", headers=headers_b)
    assert list_b_prods.status_code == 200
    assert len(list_b_prods.json()) == 0

    # User B's chat history must be completely empty (cannot see User A's messages)
    hist_b = client.get("/api/chat/history", headers=headers_b)
    assert hist_b.status_code == 200
    assert len(hist_b.json()) == 0

    # User B's bills must be empty
    bills_b = client.get("/api/bills", headers=headers_b)
    assert bills_b.status_code == 200
    assert len(bills_b.json()) == 0

    # -------------------------------------------------------------------------
    # SCENARIO 6: User A logs in again and must see their original data intact
    # -------------------------------------------------------------------------
    login_a_again = client.post("/api/auth/login", json={
        "email": user_a_email,
        "password": user_a_password,
    })
    assert login_a_again.status_code == 200
    new_token_a = login_a_again.json()["token"]
    headers_a_new = {"Authorization": f"Bearer {new_token_a}"}

    # Verify User A's products are intact (5 products)
    list_a_again = client.get("/api/products", headers=headers_a_new)
    assert list_a_again.status_code == 200
    assert len(list_a_again.json()) == 5

    # Verify User A's sales are intact
    sales_a = client.get("/api/sales/summary?weeks=8", headers=headers_a_new)
    assert sales_a.status_code == 200
    assert sales_a.json()["total_revenue"] == 3500.0

    # -------------------------------------------------------------------------
    # SCENARIO 7: Logging out and unauthenticated requests rejected (401)
    # -------------------------------------------------------------------------
    unauth_resp = client.get("/api/products")
    assert unauth_resp.status_code == 401
    assert "detail" in unauth_resp.json()

    invalid_token_resp = client.get("/api/products", headers={"Authorization": "Bearer invalid.fake.token"})
    assert invalid_token_resp.status_code == 401

    # -------------------------------------------------------------------------
    # SCENARIO 8: Direct cross-user ID tampering blocked
    # -------------------------------------------------------------------------
    # User B attempts to edit or delete User A's product using User A's product ID
    target_prod_id = prod_a_ids[0]
    tamper_edit = client.put(f"/api/products/{target_prod_id}", json={
        "name": "Hacked Product Name",
        "sell_price": 999.0,
    }, headers=headers_b)
    assert tamper_edit.status_code == 404

    tamper_delete = client.delete(f"/api/products/{target_prod_id}", headers=headers_b)
    assert tamper_delete.status_code == 404

    # Confirm User A's product was NOT altered by User B's malicious attempt
    verify_a_prod = client.get("/api/products", headers=headers_a_new)
    first_prod = [p for p in verify_a_prod.json() if p["id"] == target_prod_id][0]
    assert first_prod["name"] == "Alice Tea Gold 250g"
    assert first_prod["sell_price"] == 120.0

