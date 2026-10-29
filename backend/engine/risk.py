"""
Risk cap module (risk.py)
Spec:
  max_loss = units_cap * (before_gp - after_gp)
  units_cap = risk_budget / (before_gp - after_gp)
  Cap offer to first N customers/units.
"""
from __future__ import annotations
import math


def compute_risk_cap(
    before_gp: float,
    after_gp: float,
    risk_budget_inr: float,
) -> dict:
    """
    Returns units_cap and max_loss given the merchant's risk budget.
    before_gp and after_gp are per-unit (or per-bundle) gross profits.
    """
    gp_loss_per_unit = before_gp - after_gp
    if gp_loss_per_unit <= 0:
        # Offer increases GP — no cap needed
        return {
            "units_cap": None,
            "max_loss_inr": 0.0,
            "gp_loss_per_unit": 0.0,
            "risk_budget_inr": risk_budget_inr,
            "note": "Offer increases gross profit — no risk cap needed.",
        }

    units_cap = math.floor(risk_budget_inr / gp_loss_per_unit)
    max_loss = round(units_cap * gp_loss_per_unit, 2)

    return {
        "units_cap": units_cap,
        "max_loss_inr": max_loss,
        "gp_loss_per_unit": round(gp_loss_per_unit, 2),
        "risk_budget_inr": risk_budget_inr,
        "note": f"Limit offer to first {units_cap} units/customers to cap max loss at ₹{max_loss}.",
    }

