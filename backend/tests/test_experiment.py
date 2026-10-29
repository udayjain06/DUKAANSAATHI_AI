"""Tests for experiment net lift and GP change calculation."""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.models import Base
from engine.seed import run_seed
from engine.experiment import create_simulated_experiment, get_experiment_result
from engine.risk import compute_risk_cap


@pytest.fixture(scope="module")
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    run_seed(session, shop_type="kirana")
    yield session
    session.close()


def test_experiment_is_simulated(db):
    exp = create_simulated_experiment(
        db, "off_test001", 1,
        treatment_product_ids=[1, 2],
        control_product_ids=[3, 4],
        cost_per_unit=14, sell_price=20, discount_pct=15,
    )
    result = get_experiment_result(db, exp.id)
    assert result["is_simulated"] is True
    assert result["data_label"] == "synthetic"


def test_net_lift_calculation(db):
    """net_lift = treatment_change - control_change."""
    exp = create_simulated_experiment(
        db, "off_test002", 1,
        treatment_product_ids=[1], control_product_ids=[2],
        cost_per_unit=14, sell_price=20, discount_pct=15,
    )
    result = get_experiment_result(db, exp.id)
    t = result["treatment"]
    c = result["control"]
    expected_lift = round(t["change_pct"] - c["change_pct"], 2)
    assert abs(result["net_lift_pct"] - expected_lift) < 0.1


def test_experiment_has_gp_change(db):
    exp = create_simulated_experiment(
        db, "off_test003", 1,
        treatment_product_ids=[1], control_product_ids=[2],
        cost_per_unit=14, sell_price=20, discount_pct=15,
    )
    result = get_experiment_result(db, exp.id)
    assert "gp_change_inr" in result
    assert isinstance(result["gp_change_inr"], (int, float))


def test_risk_cap_budget():
    """Units cap must ensure max_loss <= risk_budget."""
    result = compute_risk_cap(before_gp=30, after_gp=10, risk_budget_inr=400)
    assert result["max_loss_inr"] <= 400
    assert result["units_cap"] == 20  # 400 / 20 = 20 units

def test_risk_cap_no_loss():
    """When after_gp >= before_gp, no cap is needed."""
    result = compute_risk_cap(before_gp=10, after_gp=20, risk_budget_inr=400)
    assert result["units_cap"] is None
    assert result["max_loss_inr"] == 0.0

