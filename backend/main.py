"""
DukaanSaathi AI — FastAPI main entrypoint
"""
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from db.session import init_db
from api.routes_merchant import router as merchant_router
from api.routes_sales import router as sales_router, insights_router
from api.routes_reco import router as reco_router, bills_router, margin_router
from api.routes_offer import offer_router, experiment_router, chat_router, products_router
from api.routes_payment import router as payment_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: initialise DB and seed demo data if empty."""
    init_db()
    from db.session import SessionLocal
    from db.models import SalesDaily
    db = SessionLocal()
    try:
        count = db.query(SalesDaily).count()
        if count == 0:
            logger.info("Empty database — seeding demo data...")
            from engine.seed import run_seed
            run_seed(db, shop_type="kirana")
            logger.info("Demo data seeded.")
        else:
            logger.info(f"Database already has {count} sales records.")
    finally:
        db.close()
    yield


app = FastAPI(
    title="DukaanSaathi AI — Backend API",
    description=(
        "Merchant analytics, recommendation engine, margin calculator, "
        "experiment measurement, and Paytm payment integration."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
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


@app.get("/")
def root():
    return {
        "app": "DukaanSaathi AI",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running",
    }


@app.post("/api/reset")
def reset_database():
    """Reset and reseed demo database. One-command demo reset."""
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

