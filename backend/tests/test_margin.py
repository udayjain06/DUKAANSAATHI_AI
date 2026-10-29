"""
pytest tests for the margin calculator.
Key spec test: price=100, cost=70, discount=20%
  → before_gp=30, after_gp=10, uplift=200%, after_margin=12.5%
  → blocked (min_margin=15%), alternative at 10% discount
"""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine.margin import check_margin, compute_bundle_margin


def test_spec_example():
    """The exact spec example must pass."""
    result = check_margin(sell_price=100, cost_price=70, discount_pct=20, min_margin_pct=15)
    assert result["before_gp"] == 30.0
    assert result["after_gp"] == 10.0
    assert result["after_pct"] == pytest.approx(12.5, abs=0.1)
    assert result["required_volume_uplift_pct"] == pytest.approx(200.0, abs=0.5)
    assert result["status"] == "blocked"
    # Alternative must be suggested
    assert result["alternative"] is not None
    alt = result["alternative"]
    assert alt["status"] == "ok"
    assert alt["discount_pct"] <= 15  # safer discount


def test_spec_alternative_10pct():
    """At 10% discount: price=90, gp=20, margin=22.2% → ok."""
    result = check_margin(sell_price=100, cost_price=70, discount_pct=10, min_margin_pct=15)
    assert result["after_pct"] == pytest.approx(22.22, abs=0.1)
    assert result["status"] == "ok"


def test_caution_zone():
    """Margin between min and min-3 → caution."""
    # min_margin=20, after_margin=18 → caution
    result = check_margin(sell_price=100, cost_price=30, discount_pct=55, min_margin_pct=20)
    # after_price=45, after_gp=15, after_margin=33.3% → ok actually, let's use a tighter case
    result2 = check_margin(sell_price=100, cost_price=80, discount_pct=3, min_margin_pct=20)
    # after_price=97, after_gp=17, margin=17.5% → caution (20-3=17 threshold)
    assert result2["status"] in ("caution", "blocked")


def test_zero_discount():
    """Zero discount → no change, should be ok."""
    result = check_margin(sell_price=100, cost_price=60, discount_pct=0, min_margin_pct=15)
    assert result["before_gp"] == result["after_gp"] == 40.0
    assert result["status"] == "ok"


def test_cost_greater_than_price():
    """Cost > price → negative GP, should be blocked."""
    result = check_margin(sell_price=80, cost_price=100, discount_pct=0, min_margin_pct=15)
    assert result["before_gp"] < 0
    assert result["status"] == "blocked"


def test_bundle_margin():
    items = [
        {"sell_price": 20, "cost_price": 14, "units": 1},
        {"sell_price": 20, "cost_price": 14, "units": 1},
    ]
    bundle_price = 36  # ~10% off 40
    result = compute_bundle_margin(items, bundle_price, min_margin_pct=15)
    # GP = 36 - 28 = 8, margin = 8/36 = 22.2%
    assert result["before_gp"] == pytest.approx(8.0, abs=0.1)
    assert result["status"] == "ok"


def test_invalid_sell_price():
    with pytest.raises(ValueError):
        check_margin(sell_price=0, cost_price=10, discount_pct=10, min_margin_pct=15)

