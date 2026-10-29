# DukaanSaathi AI

> AI-Powered Merchant Intelligence, Margin Protection & Experiment Platform for Indian Small Businesses (Kirana Stores, Bakeries & Retailers).

Built for the **Paytm Build for India Hackathon**.

---

## 🌟 Key Features

1. **Merchant Dashboard & Sales Analysis**:
   - 8-week sales revenue & transaction trend tracking.
   - Weekday-wise breakdown detecting weak sales days (e.g. Monday -15.2% dip) with consistency scoring and confidence levels (High/Medium/Low) without false statistical significance claims.
   - Top and bottom performing products with gross margin analysis.

2. **Deterministic Margin & Loss Protection Engine**:
   - Strictly deterministic financial calculations in Python — **zero AI hallucination**.
   - Verified formulas for Gross Profit, Margin %, and Required Volume Uplift.
   - Enforces margin safety statuses: `ok`, `caution`, and `blocked`.
   - Recommends safer alternative discounts whenever the merchant's minimum margin threshold is violated.
   - Enforces unit/customer risk caps: `units_cap = risk_budget / gp_loss`.

3. **In-Shop Control Group Experiments**:
   - Measures promotional effectiveness by comparing treatment items against similar control products within the same shop.
   - Separates **Net Sales Lift %** from **Gross Profit Change ₹**.
   - Transparently labels all synthetic and demo data.

4. **Wholesale Bill OCR & Inventory**:
   - Invoice and bill image upload with item, price, and quantity extraction.
   - Review and confirmation flow updating catalogue wholesale costs.

5. **Server-Side Paytm Payment Gateway Integration**:
   - Official server-side flow with HMAC-SHA256 checksum generation using `paytmchecksum`.
   - Staging gateway checkout integration.
   - Server-to-server webhook verification (`/api/payment/callback`) before updating subscription state.
   - Real-time status enquiry endpoint (`/api/payment/status/{orderId}`).

6. **Bilingual AI Assistant**:
   - Hindi (🇮🇳) and English (🇬🇧) merchant assistance.
   - Explains verified calculations in simple terms for shopkeepers.
   - Reliable template fallbacks ensure workflows never break if AI keys are not provided.

---

## 🏗️ Architecture & Tech Stack

```text
[Merchant React PWA]
        │
   REST │ JSON (Vite / Axios / Recharts)
        ▼
[FastAPI Backend]
   ├── engine/       # Sales analysis, weak-day detection, margin math, risk caps, experiments
   ├── ai/           # Bilingual chat, explanations, bill OCR, copy generation
   ├── api/          # REST route handlers (merchant, sales, reco, bills, offers, payment)
   └── db/           # SQLAlchemy models & SQLite session
        │
        ├── [SQLite / PostgreSQL]
        └── [Paytm Payment Gateway (Staging / Production)]
```

---

## 🚀 Quickstart & Local Setup

### Prerequisites
- Python 3.11+
- Node.js 18+ and pnpm

### 1. Backend Setup
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```
API Documentation will be available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

### 2. Frontend Setup
```bash
cd frontend
pnpm install
pnpm dev --port 5173
```
Open [http://127.0.0.1:5173](http://127.0.0.1:5173) in your browser.

---

## 🧪 Running Automated Tests

Run the full pytest suite for margin calculations, risk caps, weak-day detection, and experiment net lift:

```bash
cd backend
pytest -v
```

---

## 📄 License
MIT License.
