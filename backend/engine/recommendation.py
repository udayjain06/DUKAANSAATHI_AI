"""
Recommendation assembly (recommendation.py)
Assembles weak day + margin + risk into a full recommendation card.
Calls ai.explain() and falls back to template text if AI is unavailable.
"""
from __future__ import annotations
import uuid
from sqlalchemy.orm import Session
from db.models import Merchant, Product, Recommendation
from engine.analysis import get_primary_weak_day
from engine.margin import check_margin, compute_bundle_margin
from engine.risk import compute_risk_cap


def build_recommendation(db: Session, merchant_id: int, lang: str = "hi") -> dict:
    merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()
    if not merchant:
        return {"error": "Merchant not found"}

    min_margin = merchant.min_margin_pct or 15.0
    risk_budget = merchant.risk_budget_inr or 400.0

    # Step 2: Get products for offer
    products = db.query(Product).filter(
        Product.merchant_id == merchant_id,
        Product.is_active == True,
        Product.cost_price.isnot(None),
    ).all()

    if not products:
        return {
            "status": "insufficient_data",
            "message": "Add at least one product with cost price in the Products tab to generate AI recommendations.",
            "recommendation": None,
        }

    # Step 1: Detect weak day
    weak_day_info = get_primary_weak_day(db, merchant_id)
    if not weak_day_info:
        weak_day_info = {"weekday": "Monday", "dip_pct": 12.0, "confidence": "preliminary", "data_label": "preliminary"}

    if len(products) < 2:
        offer_type = "discount"
    else:
        offer_type = "bundle"

    offer, margin, risk = _build_offer(products, offer_type, min_margin, risk_budget)

    # Step 3: AI explanation (with fallback)
    explanation = _get_explanation(
        weak_day=weak_day_info["weekday"],
        dip_pct=weak_day_info["dip_pct"],
        offer=offer,
        margin=margin,
        risk=risk,
        lang=lang,
    )

    rec_id = "rec_" + str(uuid.uuid4())[:8]
    data_label = "synthetic"

    # Persist recommendation
    rec = Recommendation(
        id=rec_id,
        merchant_id=merchant_id,
        weak_day=weak_day_info["weekday"],
        dip_pct=weak_day_info["dip_pct"],
        offer_json=offer,
        margin_json=margin,
        risk_json=risk,
        explanation_json=explanation,
        status="pending",
        data_label=data_label,
    )
    db.add(rec)
    db.commit()

    return _rec_to_dict(rec, weak_day_info)


def _build_offer(products, offer_type, min_margin, risk_budget) -> tuple:
    if offer_type == "bundle" and len(products) >= 2:
        p1, p2 = products[0], products[1]
        bundle_price = round((p1.sell_price + p2.sell_price) * 0.9, 0)
        margin = compute_bundle_margin(
            items=[
                {"sell_price": p1.sell_price, "cost_price": p1.cost_price, "units": 1},
                {"sell_price": p2.sell_price, "cost_price": p2.cost_price, "units": 1},
            ],
            bundle_price=bundle_price,
            min_margin_pct=min_margin,
        )
        offer = {
            "type": "bundle",
            "items": [p1.name, p2.name],
            "individual_prices": [p1.sell_price, p2.sell_price],
            "bundle_price": bundle_price,
            "discount_pct": round((1 - bundle_price / (p1.sell_price + p2.sell_price)) * 100, 1),
        }
        risk = compute_risk_cap(margin["before_gp"], margin["after_gp"], risk_budget)
    else:
        # Discount on single best product
        prod = products[0] if products else None
        if not prod:
            return {"type": "discount", "items": [], "discount_pct": 10}, {
                "before_pct": 30, "after_pct": 20, "min_required_pct": min_margin,
                "status": "ok", "before_gp": 30, "after_gp": 20
            }, {"units_cap": 40, "max_loss_inr": 400}

        discount_pct = 15.0
        margin = check_margin(prod.sell_price, prod.cost_price, discount_pct, min_margin)

        # If blocked, try alternative discount
        if margin["status"] == "blocked" and margin.get("alternative"):
            discount_pct = margin["alternative"]["discount_pct"]
            margin = check_margin(prod.sell_price, prod.cost_price, discount_pct, min_margin)

        offer = {
            "type": "discount",
            "items": [prod.name],
            "original_price": prod.sell_price,
            "discount_pct": discount_pct,
            "discounted_price": round(prod.sell_price * (1 - discount_pct / 100), 2),
        }
        risk = compute_risk_cap(margin["before_gp"], margin["after_gp"], risk_budget)

    return offer, margin, risk


def _get_explanation(weak_day, dip_pct, offer, margin, risk, lang) -> dict:
    try:
        from ai.interfaces import ai_explain
        facts = {
            "weak_day": weak_day,
            "dip_pct": dip_pct,
            "offer": offer,
            "margin_after_pct": margin.get("after_pct"),
            "max_loss_inr": risk.get("max_loss_inr"),
            "units_cap": risk.get("units_cap"),
        }
        hi = ai_explain(facts, "hi")
        en = ai_explain(facts, "en")
    except Exception:
        hi, en = _template_explanation(weak_day, dip_pct, offer, margin, risk, "hi"), \
                 _template_explanation(weak_day, dip_pct, offer, margin, risk, "en")
    return {"hi": hi, "en": en}


def _template_explanation(weak_day, dip_pct, offer, margin, risk, lang) -> str:
    offer_name = offer.get("items", ["product"])[0] if offer.get("items") else "product"
    discount = offer.get("discount_pct", 10)
    max_loss = risk.get("max_loss_inr", 0)
    units_cap = risk.get("units_cap", "N/A")
    margin_after = margin.get("after_pct", 0)
    margin_status = margin.get("status", "ok")

    if lang == "hi":
        return (
            f"{weak_day} ko bikri {dip_pct:.1f}% kam hoti hai. "
            f"'{offer_name}' par {discount}% offer de kar is din mein zyada customers ko attract karo. "
            f"Offer sirf pehle {units_cap} customers ke liye—maximum loss sirf ₹{max_loss}. "
            f"Discount ke baad margin {margin_after:.1f}% rahega ({margin_status})."
        )
    else:
        return (
            f"Sales dip {dip_pct:.1f}% on {weak_day}. "
            f"Offer {discount}% off on '{offer_name}' to attract more customers. "
            f"Capped at {units_cap} units—max possible loss only ₹{max_loss}. "
            f"Post-discount margin: {margin_after:.1f}% (status: {margin_status})."
        )


def _rec_to_dict(rec: Recommendation, weak_day_info: dict) -> dict:
    return {
        "id": rec.id,
        "weak_day": rec.weak_day,
        "dip_pct": rec.dip_pct,
        "confidence": weak_day_info.get("confidence", "medium"),
        "offer": rec.offer_json,
        "margin": rec.margin_json,
        "risk": rec.risk_json,
        "explanation": rec.explanation_json,
        "status": rec.status,
        "data_label": rec.data_label,
    }


def get_pending_recommendations(db: Session, merchant_id: int) -> list[dict]:
    recs = db.query(Recommendation).filter(
        Recommendation.merchant_id == merchant_id,
        Recommendation.status == "pending",
    ).order_by(Recommendation.created_at.desc()).limit(5).all()

    return [
        {
            "id": r.id, "weak_day": r.weak_day, "dip_pct": r.dip_pct,
            "offer": r.offer_json, "margin": r.margin_json,
            "risk": r.risk_json, "explanation": r.explanation_json,
            "status": r.status, "data_label": r.data_label,
        }
        for r in recs
    ]


def apply_decision(db: Session, rec_id: str, decision: str, modified_offer: dict = None) -> dict:
    rec = db.query(Recommendation).filter(Recommendation.id == rec_id).first()
    if not rec:
        return {"error": "Recommendation not found"}

    valid = {"approved", "modified", "rejected"}
    if decision not in valid:
        return {"error": f"Decision must be one of {valid}"}

    from datetime import datetime, timezone
    rec.status = decision
    rec.decided_at = datetime.now(timezone.utc).replace(tzinfo=None)
    if decision == "modified" and modified_offer:
        rec.modified_offer_json = modified_offer
    db.commit()
    return {"id": rec_id, "status": rec.status, "decided_at": str(rec.decided_at)}

