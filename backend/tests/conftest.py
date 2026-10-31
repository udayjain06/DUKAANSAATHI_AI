"""
Pytest configuration for DukaanSaathi AI.
Ensures tests run deterministically against isolated SQLite database.
"""
import os
import pytest

# Ensure isolated SQLite is used for all automated tests
os.environ["DATABASE_URL"] = "sqlite:///./test_dukaansaathi.db"
os.environ["APP_ENV"] = "testing"

from db.session import init_db, SessionLocal, engine
from db.models import Base
from engine.seed import run_seed

@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Create test tables and seed initial demo data once per test session."""
    init_db()
    db = SessionLocal()
    try:
        from db.models import SalesDaily
        if db.query(SalesDaily).count() == 0:
            run_seed(db, shop_type="kirana")
    finally:
        db.close()
    yield
    # Clean up test DB after test suite completes
    try:
        db.close()
        Base.metadata.drop_all(bind=engine)
    except Exception:
        pass

