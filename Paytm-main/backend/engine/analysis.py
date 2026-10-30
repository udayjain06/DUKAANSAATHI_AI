"""
Weak-day detection (analysis.py)
Spec formulas:
  baseline = average of the other 6 weekdays
  dip_pct  = (baseline - day_avg) / baseline * 100
  weak if dip_pct > 10
  consistency = weeks where that day was below baseline
  confidence: ≥7 → high, 5–6 → medium, <5 → low
"""
from __future__ import annotations
import pandas as pd
from sqlalchemy.orm import Session
from db.models import SalesDaily, SalesProductDaily, Product

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
WEAK_DIP_THRESHOLD = 10.0  # percent


def get_sales_df(db: Session, merchant_id: int, weeks: int = 8) -> pd.DataFrame:
    rows = db.query(SalesDaily).filter(SalesDaily.merchant_id == merchant_id).all()
    if not rows:
        return pd.DataFrame()
    data = [
        {"date": r.date, "weekday": r.weekday, "total_amount": r.total_amount,
         "txn_count": r.txn_count, "is_synthetic": r.is_synthetic}
        for r in rows
    ]
    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")
    if weeks:
        cutoff = df["date"].max() - pd.Timedelta(weeks=weeks)
        df = df[df["date"] >= cutoff]
    return df


def get_weekday_summary(df: pd.DataFrame) -> dict:
    """Return per-weekday averages and baseline."""
    if df.empty:
        return {}
    avg = df.groupby("weekday")["total_amount"].mean().to_dict()
    # Ensure all weekdays present
    result = {day: round(avg.get(day, 0), 2) for day in WEEKDAYS}
    return result


def detect_weak_days(db: Session, merchant_id: int, weeks: int = 8) -> list[dict]:
    df = get_sales_df(db, merchant_id, weeks)
    if df.empty:
        return []

    weekday_avg = get_weekday_summary(df)
    results = []

    for day in WEEKDAYS:
        day_avg = weekday_avg.get(day, 0)
        other_avgs = [v for k, v in weekday_avg.items() if k != day and v > 0]
        if not other_avgs or day_avg == 0:
            continue
        baseline = sum(other_avgs) / len(other_avgs)
        dip_pct = (baseline - day_avg) / baseline * 100 if baseline > 0 else 0

        # Consistency: how many weeks was this day below baseline
        day_rows = df[df["weekday"] == day]["total_amount"].values
        weeks_below = sum(1 for v in day_rows if v < baseline)
        total_weeks = len(day_rows)

        if total_weeks >= 4:
            ratio = weeks_below / total_weeks
            if ratio >= 0.875:  # 7/8
                confidence = "high"
            elif ratio >= 0.625:  # 5/8
                confidence = "medium"
            else:
                confidence = "low"
        else:
            confidence = "low"

        results.append({
            "weekday": day,
            "day_avg": round(day_avg, 2),
            "baseline": round(baseline, 2),
            "dip_pct": round(dip_pct, 2),
            "is_weak": dip_pct > WEAK_DIP_THRESHOLD,
            "consistency": f"{weeks_below} of {total_weeks} weeks",
            "confidence": confidence,
        })

    results.sort(key=lambda x: -x["dip_pct"])
    return results


def get_primary_weak_day(db: Session, merchant_id: int) -> dict | None:
    weak = [d for d in detect_weak_days(db, merchant_id) if d["is_weak"]]
    if not weak:
        return None
    return weak[0]  # largest dip first


def get_sales_summary(db: Session, merchant_id: int, weeks: int = 8) -> dict:
    """Weekly and weekday-level summary for charts."""
    df = get_sales_df(db, merchant_id, weeks)
    if df.empty:
        return {"weekly": [], "weekday_avg": {}, "total_revenue": 0, "total_txns": 0}

    # Weekly totals
    df["week"] = df["date"].dt.to_period("W").astype(str)
    weekly = df.groupby("week").agg(
        revenue=("total_amount", "sum"),
        txns=("txn_count", "sum"),
        days=("total_amount", "count"),
    ).reset_index()
    weekly_list = weekly.sort_values("week").to_dict(orient="records")

    weekday_avg = get_weekday_summary(df)

    # Best / worst day
    best_day = max(weekday_avg, key=lambda k: weekday_avg[k]) if weekday_avg else None
    worst_day = min(weekday_avg, key=lambda k: weekday_avg[k]) if weekday_avg else None

    return {
        "weekly": weekly_list,
        "weekday_avg": weekday_avg,
        "total_revenue": round(df["total_amount"].sum(), 2),
        "total_txns": int(df["txn_count"].sum()),
        "avg_daily_revenue": round(df["total_amount"].mean(), 2),
        "best_day": best_day,
        "worst_day": worst_day,
        "data_label": "synthetic" if df["is_synthetic"].all() else "real",
    }


def get_product_insights(db: Session, merchant_id: int, weeks: int = 8) -> dict:
    """Top / low performing products."""
    from datetime import date, timedelta
    import pandas as pd

    rows = db.query(SalesProductDaily).filter(
        SalesProductDaily.merchant_id == merchant_id
    ).all()
    if not rows:
        return {"top": [], "low": []}

    products = {p.id: p for p in db.query(Product).filter(Product.merchant_id == merchant_id).all()}
    data = [
        {"product_id": r.product_id, "units": r.units, "revenue": r.revenue,
         "date": r.date}
        for r in rows
    ]
    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])
    cutoff = pd.Timestamp.today() - pd.Timedelta(weeks=weeks)
    df = df[df["date"] >= cutoff]

    summary = df.groupby("product_id").agg(total_units=("units", "sum"), total_revenue=("revenue", "sum")).reset_index()
    summary = summary.sort_values("total_revenue", ascending=False)

    def enrich(row):
        p = products.get(int(row["product_id"]))
        if not p:
            return None
        margin = round((p.sell_price - (p.cost_price or 0)) / p.sell_price * 100, 1) if p.cost_price else None
        return {
            "product_id": int(row["product_id"]),
            "name": p.name,
            "category": p.category,
            "total_units": int(row["total_units"]),
            "total_revenue": round(float(row["total_revenue"]), 2),
            "sell_price": p.sell_price,
            "cost_price": p.cost_price,
            "margin_pct": margin,
        }

    records = [enrich(r) for _, r in summary.iterrows()]
    records = [r for r in records if r]
    return {
        "top": records[:4],
        "low": records[-4:][::-1] if len(records) >= 4 else [],
    }

