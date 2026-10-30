"""
Margin calculator (margin.py) — pitch ka dil
All formulas match the spec exactly.

Example from spec:
  price=100, cost=70, discount=20%
  before_gp = 30, after_gp = 10
  required_volume_uplift = 30/10 - 1 = 2.0 → 200%
  after_margin = 10/80 * 100 = 12.5%

Status rules:
  ok       : after_margin >= min_margin
  caution  : after_margin >= min_margin - 3
  blocked  : after_margin < min_margin - 3
"""
from __future__ import annotations
from typing import Optional


def check_margin(
    sell_price: float,
    cost_price: float,
    discount_pct: float,
    min_margin_pct: float,
    bundle_price: Optional[float] = None,
    bundle_cost: Optional[float] = None,
) -> dict:
    """
    Calculate margin before/after discount (or bundle).
    Returns full margin dict compatible with recommendation response shape.
    """
    if sell_price <= 0:
        raise ValueError("sell_price must be > 0")
    if cost_price is None or cost_price < 0:
        raise ValueError("cost_price must be >= 0")

    # Bundle path
    if bundle_price is not None and bundle_cost is not None:
        before_gp = bundle_price - bundle_cost
        before_margin = before_gp / bundle_price * 100
        # discount applied to bundle price
        after_price = bundle_price * (1 - discount_pct / 100)
        after_gp = after_price - bundle_cost
        after_margin = after_gp / after_price * 100 if after_price > 0 else 0
        required_volume_uplift = (before_gp / after_gp - 1) * 100 if after_gp > 0 else float("inf")
        status, alt = _status_and_alt(after_margin, min_margin_pct, bundle_price, bundle_cost, discount_pct, is_bundle=True)
        return {
            "before_gp": round(before_gp, 2),
            "after_gp": round(after_gp, 2),
            "before_pct": round(before_margin, 2),
            "after_pct": round(after_margin, 2),
            "min_required_pct": min_margin_pct,
            "required_volume_uplift_pct": round(required_volume_uplift, 2) if after_gp > 0 else None,
            "status": status,
            "alternative": alt,
        }

    # Single product path
    before_gp = sell_price - cost_price
    before_margin = before_gp / sell_price * 100

    after_price = sell_price * (1 - discount_pct / 100)
    if after_price <= 0:
        after_gp = -cost_price
        after_margin = -9999.0
    else:
        after_gp = after_price - cost_price
        after_margin = after_gp / after_price * 100

    if before_gp > 0 and after_gp > 0:
        required_volume_uplift = (before_gp / after_gp - 1) * 100
    elif after_gp <= 0:
        required_volume_uplift = float("inf")
    else:
        required_volume_uplift = 0.0

    status, alt = _status_and_alt(after_margin, min_margin_pct, sell_price, cost_price, discount_pct)

    return {
        "before_gp": round(before_gp, 2),
        "after_gp": round(after_gp, 2),
        "before_pct": round(before_margin, 2),
        "after_pct": round(after_margin, 2),
        "min_required_pct": min_margin_pct,
        "required_volume_uplift_pct": round(required_volume_uplift, 2) if required_volume_uplift != float("inf") else None,
        "status": status,
        "alternative": alt,
    }


def _status_and_alt(
    after_margin: float,
    min_margin_pct: float,
    sell_price: float,
    cost_price: float,
    discount_pct: float,
    is_bundle: bool = False,
) -> tuple[str, Optional[dict]]:
    # If margin is below min_margin, we also suggest safer alternative
    alt = _find_safe_alternative(sell_price, cost_price, min_margin_pct, is_bundle)
    if after_margin >= min_margin_pct:
        return "ok", None
    elif after_margin >= min_margin_pct - 2.0:
        return "caution", alt
    else:
        return "blocked", alt


def _find_safe_alternative(
    sell_price: float,
    cost_price: float,
    min_margin_pct: float,
    is_bundle: bool = False,
) -> Optional[dict]:
    """Binary search for max discount that keeps margin >= min_margin_pct."""
    for trial_discount in range(15, 0, -1):
        ap = sell_price * (1 - trial_discount / 100)
        if ap <= 0:
            continue
        gp = ap - cost_price
        margin = gp / ap * 100
        if margin >= min_margin_pct:
            return {
                "discount_pct": trial_discount,
                "after_price": round(ap, 2),
                "after_gp": round(gp, 2),
                "after_margin_pct": round(margin, 2),
                "status": "ok",
                "message": f"Try {trial_discount}% discount instead — margin will be {round(margin,1)}%.",
            }
    return None


def compute_bundle_margin(
    items: list[dict],  # [{sell_price, cost_price, units}]
    bundle_price: float,
    min_margin_pct: float,
) -> dict:
    total_cost = sum(i["cost_price"] * i.get("units", 1) for i in items)
    before_gp = bundle_price - total_cost
    before_margin = before_gp / bundle_price * 100 if bundle_price > 0 else 0

    status, alt = _status_and_alt(before_margin, min_margin_pct, bundle_price, total_cost, 0, is_bundle=True)
    return {
        "bundle_price": bundle_price,
        "total_cost": round(total_cost, 2),
        "before_gp": round(before_gp, 2),
        "after_gp": round(before_gp, 2),  # no additional discount in bundle
        "before_pct": round(before_margin, 2),
        "after_pct": round(before_margin, 2),
        "min_required_pct": min_margin_pct,
        "status": status,
        "alternative": alt,
    }

