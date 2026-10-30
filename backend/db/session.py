"""
Database session management.
Supports local SQLite development and production PostgreSQL / Supabase Transaction Poolers.
"""
import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

RAW_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./dukaansaathi.db")


def normalize_database_url(url: str) -> str:
    """
    Normalize PostgreSQL database URLs for SQLAlchemy 2.0 and psycopg compatibility.
    Supabase and cloud providers often provide 'postgres://' or 'postgresql://' strings.
    """
    if not url:
        return "sqlite:///./dukaansaathi.db"
    
    clean_url = url.strip()
    
    # Handle deprecated postgres:// prefix
    if clean_url.startswith("postgres://"):
        clean_url = "postgresql+psycopg://" + clean_url[len("postgres://"):]
    # If postgresql:// is provided without explicit driver, use psycopg (v3)
    elif clean_url.startswith("postgresql://") and not clean_url.startswith("postgresql+"):
        clean_url = "postgresql+psycopg://" + clean_url[len("postgresql://"):]
        
    return clean_url


DATABASE_URL = normalize_database_url(RAW_DATABASE_URL)

connect_args = {}
engine_kwargs = {}

if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False
else:
    # PostgreSQL / Supabase configuration
    # Disable prepared statements in psycopg3 for Supabase Transaction Pooler (pgbouncer) compatibility
    if "psycopg" in DATABASE_URL and "psycopg2" not in DATABASE_URL:
        connect_args["prepare_threshold"] = None

    engine_kwargs.update({
        "pool_pre_ping": True,     # Verify connections before checkout to handle cloud drops
        "pool_recycle": 300,       # Recycle connections every 5 minutes
        "pool_size": 5,            # Safe connection limit for poolers and serverless
        "max_overflow": 10,
    })

logger.info(f"Initialising database engine with dialect: {DATABASE_URL.split('://')[0]}")
engine = create_engine(DATABASE_URL, connect_args=connect_args, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI dependency for database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Safely initialize schema.
    create_all only creates tables that do not exist yet without modifying or dropping existing tables.
    """
    from db.models import Base
    Base.metadata.create_all(bind=engine)
