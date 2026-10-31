"""
DukaanSaathi AI — FastAPI main entrypoint.
Production-ready for Render, Supabase PostgreSQL, and Vercel frontend.
"""
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from db.session import init_db
from api.routes_auth import router as auth_router
from api.routes_merchant import router as merchant_router
from api.routes_sales import router as sales_router, insights_router
from api.routes_reco import router as reco_router, bills_router, margin_router
from api.routes_offer import offer_router, experiment_router, chat_router, products_router
from api.routes_payment import router as payment_router
from api.routes_user_dashboard import router as user_router, ml_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Parse ALLOWED_ORIGINS safely
raw_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000"
)
allowed_origins = [o.strip() for o in raw_origins.split(",") if o.strip()]

APP_ENV = os.getenv("APP_ENV", "production").lower()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: initialise DB and seed demo data if empty."""
    try:
        init_db()
        from db.session import SessionLocal
        db = SessionLocal()
        try:
            from engine.seed import ensure_demo_data
            ensure_demo_data(db)
            logger.info("Startup data check complete (demo seed + ML corpus).")
        finally:
            db.close()
    except Exception as exc:
        logger.error(f"Database initialization warning at startup: {exc}")
        logger.warning(
            "Application started in resilient mode. Ensure your DATABASE_URL uses the IPv4 connection pooler on Render."
        )
    yield


app = FastAPI(
    title="DukaanSaathi AI — Backend API",
    description=(
        "Merchant analytics, recommendation engine, margin calculator, "
        "ML spending predictions, Paytm gateway, and Groq AI integration."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS Configuration — Allows localhost and any Vercel deployment (*.vercel.app)
if "*" in allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_origin_regex=r"^https://.*\.vercel\.app$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# Register routers
app.include_router(auth_router)
app.include_router(merchant_router)
app.include_router(sales_router)
app.include_router(insights_router)
app.include_router(reco_router)
app.include_router(bills_router)
app.include_router(margin_router)
app.include_router(offer_router)
app.include_router(experiment_router)
app.include_router(chat_router)
app.include_router(products_router)
app.include_router(payment_router)
app.include_router(user_router)
app.include_router(ml_router)


@app.get("/")
def root():
    return {
        "app": "DukaanSaathi AI",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running",
        "environment": APP_ENV,
    }


@app.get("/health")
@app.get("/api/health")
def health_check():
    """Health check for Render, load balancers, and monitoring."""
    return {
        "status": "healthy",
        "app": "DukaanSaathi AI",
        "environment": APP_ENV,
    }


@app.post("/api/reset")
def reset_database():
    """Reset and reseed demo database. Blocked in production to protect data."""
    raw_db = os.getenv("DATABASE_URL", "")
    if APP_ENV == "production" or ("sqlite" not in raw_db and raw_db != ""):
        raise HTTPException(
            status_code=403,
            detail="Database reset is disabled in production environments to protect persistent data."
        )

    from db.session import SessionLocal, engine
    from db.models import Base
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        from engine.seed import run_seed
        run_seed(db, shop_type="kirana")
    finally:
        db.close()
    return {"status": "reset_complete", "message": "Database reset and demo data reseeded."}
