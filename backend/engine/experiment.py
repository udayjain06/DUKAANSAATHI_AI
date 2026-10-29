"""
Experiment measurement (experiment.py)
Spec:
  net_lift = treatment_change_pct - control_change_pct
  gp_change = (after_revenue - after_cost) - (before_revenue - before_cost)
  All results labelled is_simulated=True for demo data.
"""
from __future__ import annotations
import random
import uuid
from datetime import date, timedelta
from sqlalchemy.orm import Session
from db.models import Experiment, Offer, SalesProductDaily, Product

random.seed(42)


def simulate_after_period(
    before_units: int,
    lift_assumption_pct: float = 25.0,
    noise_pct: float = 5.0,
) -> int:
    """Simulate after-period units with a fixed lift assumption."""
    noise = random.uniform(-noise_pct, noise_pct)
    after_units = int(before_units * (1 + (lift_assumption_pct + noise) / 100))
    return max(after_units, 1)


def get_experiment_result(db: Session, experiment_id: str) -> dict:
    exp = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if not exp:
        return {"error": "Experiment not found"}

    before = exp.before_period_json or {}
    after = exp.after_period_json or {}

    t_before_units = before.get("treatment_units", 0)
    t_after_units = after.get("treatment_units", t_before_units)
    c_before_units = before.get("control_units", 0)
    c_after_units = after.get("control_units", c_before_units)

    t_change = ((t_after_units - t_before_units) / t_before_units * 100) if t_before_units else 0
    c_change = ((c_after_units - c_before_units) / c_before_units * 100) if c_before_units else 0
    net_lift = round(t_change - c_change, 2)

    # GP change
    t_before_gp = before.get("treatment_gp", 0)
    t_after_gp = after.get("treatment_gp", t_before_gp)
    gp_change = round(t_after_gp - t_before_gp, 2)

    return {
        "experiment_id": experiment_id,
        "treatment": {
            "before_units": t_before_units,
            "after_units": t_after_units,
            "change_pct": round(t_change, 2),
        },
        "control": {
            "before_units": c_before_units,
            "after_units": c_after_units,
            "change_pct": round(c_change, 2),
        },
        "net_lift_pct": net_lift,
        "gp_change_inr": gp_change,
        "is_simulated": exp.is_simulated,
        "data_label": exp.data_label,
        "interpretation": _interpret(net_lift, gp_change),
        "disclaimer": "These are simulated/indicative results, not proven real-world outcomes.",
    }


def _interpret(net_lift: float, gp_change: float) -> str:
    if net_lift > 20 and gp_change > 0:
        return "Strong positive lift with improved gross profit."
    elif net_lift > 10:
        return "Moderate positive lift. Monitor gross profit closely."
    elif net_lift > 0:
        return "Small positive lift. Consider extending or refining the offer."
    else:
        return "No significant lift detected. Review offer design."


def create_simulated_experiment(
    db: Session,
    offer_id: str,
    merchant_id: int,
    treatment_product_ids: list[int],
    control_product_ids: list[int],
    cost_per_unit: float = 0,
    sell_price: float = 0,
    discount_pct: float = 0,
) -> Experiment:
    """Create a simulated experiment for demo purposes."""
    # Estimate before period units from sales data
    t_before = random.randint(80, 140)
    c_before = random.randint(150, 230)

    lift_assumption = max(20.0, 30.0 - discount_pct)  # rough assumption
    t_after = simulate_after_period(t_before, lift_assumption)
    c_after = simulate_after_period(c_before, 5.0)  # control: slight natural growth

    after_price = sell_price * (1 - discount_pct / 100) if sell_price else sell_price
    t_before_gp = t_before * (sell_price - cost_per_unit) if sell_price and cost_per_unit else 0
    t_after_gp = t_after * (after_price - cost_per_unit) if after_price and cost_per_unit else 0

    exp = Experiment(
        id=str(uuid.uuid4())[:12],
        offer_id=offer_id,
        merchant_id=merchant_id,
        treatment_product_ids=treatment_product_ids,
        control_product_ids=control_product_ids,
        before_period_json={
            "treatment_units": t_before,
            "control_units": c_before,
            "treatment_gp": round(t_before_gp, 2),
        },
        after_period_json={
            "treatment_units": t_after,
            "control_units": c_after,
            "treatment_gp": round(t_after_gp, 2),
        },
        net_lift_pct=round(
            ((t_after - t_before) / t_before * 100) - ((c_after - c_before) / c_before * 100), 2
        ),
        gp_change_inr=round(t_after_gp - t_before_gp, 2),
        is_simulated=True,
        data_label="synthetic",
    )
    db.add(exp)
    db.commit()
    db.refresh(exp)
    return exp

