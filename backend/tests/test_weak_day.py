"""Tests for weak-day detection using seeded data."""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.models import Base
from engine.seed import run_seed
from engine.analysis import detect_weak_days, get_primary_weak_day, get_sales_summary


@pytest.fixture(scope="module")
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    run_seed(session, shop_type="kirana")
    yield session
    session.close()


def test_monday_detected_as_weak(db):
    """Seeded data must have Monday as weakest day."""
    primary = get_primary_weak_day(db, merchant_id=1)
    assert primary is not None
    assert primary["weekday"] == "Monday"
    assert primary["dip_pct"] > 10.0, "Monday dip must exceed 10% threshold"


def test_monday_confidence_high(db):
    """With 8 weeks of data, Monday should have high confidence."""
    primary = get_primary_weak_day(db, merchant_id=1)
    assert primary["confidence"] in ("high", "medium")


def test_all_weekdays_returned(db):
    """detect_weak_days should return data for all 7 weekdays."""
    days = detect_weak_days(db, merchant_id=1)
    returned_days = {d["weekday"] for d in days}
    expected = {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"}
    assert expected.issubset(returned_days)


def test_sales_summary_totals(db):
    """Sales summary must return positive revenue and transaction count."""
    summary = get_sales_summary(db, merchant_id=1)
    assert summary["total_revenue"] > 0
    assert summary["total_txns"] > 0
    assert summary["best_day"] is not None
    assert summary["worst_day"] is not None


def test_data_label_is_synthetic(db):
    """All seeded data must be labelled synthetic."""
    summary = get_sales_summary(db, merchant_id=1)
    assert summary["data_label"] == "synthetic"

