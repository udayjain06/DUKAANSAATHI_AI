# DukaanSaathi AI

> AI-powered merchant intelligence, margin protection and experiment platform for Indian small businesses (kirana stores, bakeries and retailers).

Built for the **Paytm Build for India Hackathon**.

## Features

1. **Merchant dashboard & sales analysis** — 8-week revenue/transaction trends, weekday breakdown, weak-day detection with confidence labels, top/bottom products with margin analysis.
2. **Deterministic margin & loss protection** — Python-only financial math (no AI hallucination), `ok` / `caution` / `blocked` statuses, safer-discount alternatives, and unit/customer risk caps.
3. **In-shop control experiments** — treatment vs control comparison with net sales lift and gross-profit change, clearly labelled as simulated.
4. **Wholesale bill OCR & inventory** — upload a JPG/PNG/WebP/BMP/TIFF photo or a PDF invoice; the local RapidOCR pipeline extracts items, prices and quantities for review before updating wholesale costs. Manual entry always available.
5. **Paytm Payment Gateway** — server-side order creation with the official `paytmchecksum` library, verified callbacks, idempotent order handling, and signed status enquiry.
6. **Bilingual AI assistant** — Hindi/English merchant chat, explanations and offer copy via Groq, with deterministic local fallbacks so the app works without an API key.
7. **Secure accounts & isolation** — backend-issued JWTs (PBKDF2-HMAC-SHA256 passwords), strict per-user/per-shop data isolation, and a one-click demo account.
8. **User finance dashboard** — scikit-learn expense categorisation, spending prediction, anomaly detection, and per-user ML insights.

## Tech stack

```
React PWA (Vite) ── REST/JSON ── FastAPI
                                  ├── engine/  sales, margin, risk, experiments, ML
                                  ├── ai/      Groq chat, explanations, offer copy, local OCR
                                  ├── api/     auth, merchant, sales, recommendation, bills, offers, payment, user
                                  └── db/      SQLAlchemy models (SQLite / PostgreSQL)
```

## Project structure

```
.
├── backend/
│   ├── ai/            Groq client, interfaces, local bill OCR
│   ├── api/           FastAPI routers (auth, sales, recommendations, offers, payments, users)
│   ├── core/          JWT security, auth dependencies, shared helpers
│   ├── db/            SQLAlchemy models, engine/session, Supabase migration
│   ├── engine/        sales analysis, margin, risk, experiments, seed data, ML
│   ├── tests/         pytest regression, auth-isolation, payment and ML suites
│   ├── main.py        FastAPI entrypoint (CORS, startup seed, health)
│   ├── requirements.txt       runtime dependencies
│   ├── requirements-dev.txt   runtime + test dependencies
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/  shared UI, navigation, effects
│   │   ├── context/     auth, language, theme providers
│   │   ├── pages/       dashboard, sales, recommendations, offers, bills, payment, chat
│   │   ├── api.js       axios client with JWT interceptor
│   │   └── main.jsx
│   ├── package.json
│   └── .env.example
├── render.yaml                Render backend deployment
└── README.md
```

## Local setup

### Backend

```bash
cd backend
pip install -r requirements-dev.txt
cp .env.example .env        # set SECRET_KEY; optionally add GROQ_API_KEY / PAYTM_*
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

API docs: http://127.0.0.1:8000/docs

Use the **Demo login** button in the app, or `POST /api/auth/demo` for a token.

### Frontend

```bash
cd frontend
npm install
npm run dev -- --port 5173
```

Open http://127.0.0.1:5173. The Vite dev server proxies `/api` to `localhost:8000`; set `VITE_API_URL` for a hosted backend (see `frontend/.env.example`).

### Tests

```bash
cd backend
pytest -q
```

## Environment variables

| Variable | Purpose |
| --- | --- |
| `SECRET_KEY` | Long random string used to sign JWT access tokens (required in production) |
| `DATABASE_URL` | SQLite (default) or Supabase PostgreSQL connection string |
| `GROQ_API_KEY` | Enables live Groq chat, explanations and offer copy (optional) |
| `GROQ_MODEL` | Groq text model override |
| `PAYTM_MID` / `PAYTM_MERCHANT_KEY` | Paytm gateway credentials |
| `PAYTM_ENV` / `PAYTM_WEBSITE` / `PAYTM_CHANNEL_ID` | Paytm environment and website settings |
| `PAYTM_CALLBACK_URL` | Public backend callback URL |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins (any `*.vercel.app` is also allowed) |

Without `GROQ_API_KEY`, all AI features use deterministic local fallbacks. Without Paytm credentials, `/api/payment/initiate` returns a clear `503 payment_not_configured` response. Bill OCR runs locally and does not require any API key.

## Deployment

- Backend: Render (`render.yaml` included; `SECRET_KEY` is auto-generated).
- Database: SQLite locally or Supabase PostgreSQL in production (tables are created automatically on startup).
- Frontend: Vercel (set `VITE_API_URL` to the Render backend URL).

## Quality checks

Run these before pushing:

```bash
cd backend && pytest -q
cd frontend && npm run build
```

## License

MIT — see [LICENSE](LICENSE).
