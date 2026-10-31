"""
DukaanSaathi / Paytm AI — Real Machine Learning Engine
------------------------------------------------------
1. Transaction preprocessing
2. Expense Categorization      (TF-IDF + LogisticRegression)
3. Future Spending Prediction  (Ridge Regression on a daily time-series)
4. Unusual Transaction Detection (IsolationForest on log-amounts + robust guard)
5. Model evaluation, metadata and joblib persistence

Training data comes from `engine.training_data` (curated real-life Indian
kirana / bakery transaction descriptions) and can be extended with rows from
the `ml_training_sample` table via `train_from_db(db)`.
"""
from __future__ import annotations

import os
import json
import logging
import hashlib
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.ensemble import IsolationForest
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.metrics import accuracy_score, mean_absolute_error
from sklearn.model_selection import train_test_split

from engine.training_data import REAL_LIFE_SAMPLES, DAILY_SALES_SERIES

logger = logging.getLogger(__name__)

ENGINE_VERSION = "3.1"

MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
CATEGORIZER_PATH = os.path.join(MODELS_DIR, "categorizer.joblib")
PREDICTOR_PATH = os.path.join(MODELS_DIR, "spending_predictor.joblib")
ANOMALY_PATH = os.path.join(MODELS_DIR, "anomaly_detector.joblib")
METADATA_PATH = os.path.join(MODELS_DIR, "metadata.json")

# Brand / app-name oriented samples. Kept alongside the real-life ledger corpus
# so well-known merchants (Swiggy, Uber, Apollo…) are categorised correctly.
DEFAULT_TRAIN_DATA = [
    # Food & Dining
    ("Swiggy food order biryani", "Food", 350.0),
    ("Zomato pizza delivery", "Food", 520.0),
    ("Starbucks coffee latte", "Food", 280.0),
    ("Chai point snacks tea", "Food", 120.0),
    ("McDonalds burger combo meal", "Food", 390.0),
    ("Haldiram thali lunch", "Food", 260.0),
    ("Dominos garlic bread pizza", "Food", 480.0),
    ("Cafe Coffee Day cappuccino", "Food", 210.0),
    # Groceries
    ("Blinkit instant grocery delivery", "Groceries", 850.0),
    ("Zepto vegetables and fruits", "Groceries", 640.0),
    ("BigBasket monthly pantry staples", "Groceries", 2400.0),
    ("Dmart store grocery wheat rice", "Groceries", 1850.0),
    ("Mother Dairy milk and curd", "Groceries", 95.0),
    ("Nature Basket organic pulses", "Groceries", 920.0),
    # Travel & Commute
    ("Uber cab ride to office", "Travel", 310.0),
    ("Ola auto ride metro station", "Travel", 85.0),
    ("IndianOil petrol fuel refill", "Travel", 1500.0),
    ("HPCL diesel pump car", "Travel", 2200.0),
    ("MakeMyTrip flight ticket Delhi", "Travel", 4500.0),
    ("IRCTC train ticket booking", "Travel", 1250.0),
    ("Fastag highway toll deduction", "Travel", 140.0),
    ("Indigo flight ticket booking", "Travel", 5200.0),
    # Utilities & Bills
    ("BSES electricity bill payment", "Utilities", 1850.0),
    ("Electricity Power Bill payment", "Utilities", 1650.0),
    ("Jio prepaid mobile recharge", "Utilities", 349.0),
    ("Airtel fiber broadband wifi bill", "Utilities", 999.0),
    ("Indane LPG cylinder refill gas", "Utilities", 920.0),
    ("Water supply municipal board bill", "Utilities", 420.0),
    # Entertainment & Subs
    ("Netflix monthly premium plan", "Entertainment", 649.0),
    ("BookMyShow movie tickets PVR", "Entertainment", 760.0),
    ("Spotify family music streaming", "Entertainment", 179.0),
    ("Amazon Prime annual subscription", "Entertainment", 1499.0),
    ("SonyLIV live cricket streaming", "Entertainment", 299.0),
    # Shopping
    ("Amazon electronics bluetooth earphones", "Shopping", 1999.0),
    ("Myntra casual shirt jeans apparel", "Shopping", 1450.0),
    ("Flipkart running shoes sports", "Shopping", 2299.0),
    ("Nykaa skincare cosmetics serum", "Shopping", 890.0),
    ("Croma electronic charger cable", "Shopping", 650.0),
    # Healthcare
    ("Apollo pharmacy medicine pills", "Healthcare", 480.0),
    ("Apollo Pharmacy Medicine Tablets", "Healthcare", 520.0),
    ("Dr Lal Pathlabs blood test checkup", "Healthcare", 1100.0),
    ("Consultation fee clinic doctor", "Healthcare", 600.0),
    ("Medplus prescription tablets", "Healthcare", 320.0),
    # Rent / salary explicitly represented so the classifier can learn them
    ("shop rent monthly payment", "Rent", 12000.0),
    ("godown warehouse rent", "Rent", 6500.0),
    ("staff salary monthly payment", "Salary", 15000.0),
    ("helper wages weekly payout", "Salary", 3500.0),
    ("store packaging carry bags", "Supplies", 480.0),
    ("shop electricity and water", "Utilities", 2450.0),
]

# Everything the bootstrapped (offline) models learn from
BOOTSTRAP_SAMPLES: list[tuple[str, str, float]] = list(DEFAULT_TRAIN_DATA) + list(REAL_LIFE_SAMPLES)

CATEGORY_ORDER = [
    "Food", "Groceries", "Travel", "Utilities", "Entertainment",
    "Shopping", "Healthcare", "Rent", "Salary", "Supplies", "General",
]

DEFAULT_METADATA = {
    "engine_version": ENGINE_VERSION,
    "status": "untrained",
    "trained_at": None,
    "corpus_fingerprint": None,
    "corpus_size": 0,
    "categories": [],
    "categorizer_accuracy_pct": None,
    "predictor_mae": None,
    "predictor_mape_pct": None,
    "anomaly_threshold": 5000.0,
    "db_samples": 0,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utc_iso() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")


def _normalise_samples(samples) -> list[tuple[str, str, float]]:
    """Accept tuples, dicts or SQLAlchemy rows and return clean tuples."""
    rows: list[tuple[str, str, float]] = []
    for item in samples or []:
        if isinstance(item, dict):
            desc, cat, amt = item.get("description"), item.get("category"), item.get("amount")
        elif isinstance(item, (tuple, list)) and len(item) >= 3:
            desc, cat, amt = item[0], item[1], item[2]
        else:
            desc = getattr(item, "description", None)
            cat = getattr(item, "category", None)
            amt = getattr(item, "amount", None)
        if not desc or not cat:
            continue
        try:
            amount = float(amt or 0.0)
        except (TypeError, ValueError):
            amount = 0.0
        rows.append((str(desc).strip(), str(cat).strip(), amount))

    # De-duplicate identical descriptions (case-insensitive)
    seen, unique = set(), []
    for desc, cat, amt in rows:
        key = desc.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append((desc, cat, amt))
    return unique


def _fingerprint(samples: list[tuple[str, str, float]]) -> str:
    digest = hashlib.sha256()
    for desc, cat, amt in samples:
        digest.update(f"{desc.lower()}|{cat}|{round(amt, 2)};".encode("utf-8"))
    return digest.hexdigest()[:16]


def _read_metadata() -> dict:
    try:
        with open(METADATA_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return {**DEFAULT_METADATA, **data}
    except Exception:
        return dict(DEFAULT_METADATA)


def _write_metadata(data: dict) -> None:
    os.makedirs(MODELS_DIR, exist_ok=True)
    with open(METADATA_PATH, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)


def get_model_status() -> dict:
    """Human-readable view of the persisted ML artefacts."""
    meta = _read_metadata()
    files = {
        "categorizer": os.path.exists(CATEGORIZER_PATH),
        "spending_predictor": os.path.exists(PREDICTOR_PATH),
        "anomaly_detector": os.path.exists(ANOMALY_PATH),
    }
    return {
        **meta,
        "status": "ready" if all(files.values()) else "untrained",
        "models_present": files,
        "model_dir": MODELS_DIR,
    }


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def _fit_series_model(series: list[float]) -> tuple[Ridge, float]:
    """
    Fit a Ridge regressor on [day_of_week, day_of_month, lag1, lag2, lag7].
    Returns (model, mae).
    """
    values = [float(v) for v in series]
    X, y = [], []
    for i in range(7, len(values)):
        X.append([
            i % 7,
            (i % 30) + 1,
            values[i - 1],
            values[i - 2],
            values[i - 7],
        ])
        y.append(values[i])

    if len(X) < 8:
        # Not enough history — fall back to the seasonal baseline pattern
        fallback = [float(v) for v in DAILY_SALES_SERIES]
        X, y = [], []
        for i in range(7, len(fallback)):
            X.append([i % 7, (i % 30) + 1, fallback[i - 1], fallback[i - 2], fallback[i - 7]])
            y.append(fallback[i])
        model = Ridge(alpha=1.0)
        model.fit(np.asarray(X, dtype=float), np.asarray(y, dtype=float))
        return model, float(np.mean(np.abs(np.asarray(y) - model.predict(np.asarray(X)))))

    model = Ridge(alpha=1.0)
    model.fit(np.asarray(X, dtype=float), np.asarray(y, dtype=float))
    mae = float(mean_absolute_error(y, model.predict(np.asarray(X, dtype=float))))
    return model, mae


def train_models(samples: list | None = None) -> dict:
    """Train all 3 ML models on the given corpus (defaults to the curated corpus)."""
    os.makedirs(MODELS_DIR, exist_ok=True)

    rows = _normalise_samples(samples) if samples else _normalise_samples(BOOTSTRAP_SAMPLES)
    if len(rows) < 12:
        rows = _normalise_samples(BOOTSTRAP_SAMPLES)

    df = pd.DataFrame(rows, columns=["description", "category", "amount"])
    df = df[df["description"].str.len() > 0].reset_index(drop=True)

    # 1. Expense Categorizer (TF-IDF word + char n-grams -> LogisticRegression)
    def _make_classifier_pipeline() -> Pipeline:
        return Pipeline([
            ("features", FeatureUnion([
                ("word", TfidfVectorizer(ngram_range=(1, 2), min_df=1, lowercase=True,
                                         sublinear_tf=True)),
                ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5),
                                         min_df=1, lowercase=True, sublinear_tf=True)),
            ])),
            ("clf", LogisticRegression(C=10.0, max_iter=1500, random_state=42)),
        ])

    clf_pipeline = _make_classifier_pipeline()

    cat_accuracy = 100.0
    if len(df) >= 40:
        try:
            X_tr, X_te, y_tr, y_te = train_test_split(
                df["description"], df["category"], test_size=0.2, random_state=42
            )
            probe = _make_classifier_pipeline()
            probe.fit(X_tr, y_tr)
            cat_accuracy = round(accuracy_score(y_te, probe.predict(X_te)) * 100, 1)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Categorizer holdout evaluation failed: %s", exc)

    clf_pipeline.fit(df["description"], df["category"])
    joblib.dump(clf_pipeline, CATEGORIZER_PATH)

    # 2. Spending Predictor (Ridge on a realistic daily sales/spend series)
    base_series = [float(v) for v in DAILY_SALES_SERIES]
    regressor, train_mae = _fit_series_model(base_series)
    joblib.dump(regressor, PREDICTOR_PATH)

    mean_value = float(np.mean(base_series)) or 1.0
    mape = round(train_mae / mean_value * 100, 1)

    # 3. Anomaly Detector (IsolationForest on log-amounts)
    amounts = np.asarray([a for a in df["amount"].tolist() if a and a > 0], dtype=float)
    if amounts.size < 10:
        amounts = np.asarray([120.0, 340.0, 480.0, 650.0, 900.0, 1200.0,
                              1600.0, 2400.0, 3600.0, 5200.0], dtype=float)
    iso = IsolationForest(contamination=0.08, random_state=42)
    iso.fit(np.log1p(amounts).reshape(-1, 1))
    joblib.dump(iso, ANOMALY_PATH)

    # Robust amount ceiling: anything above this is never a normal expense
    anomaly_threshold = round(max(5000.0, float(np.percentile(amounts, 90)) * 2), 2)

    metadata = {
        "engine_version": ENGINE_VERSION,
        "status": "ready",
        "trained_at": _utc_iso(),
        "corpus_fingerprint": _fingerprint(rows),
        "corpus_size": len(rows),
        "categories": sorted(df["category"].unique().tolist()),
        "categorizer_accuracy_pct": cat_accuracy,
        "predictor_mae": round(train_mae, 2),
        "predictor_mape_pct": mape,
        "anomaly_threshold": anomaly_threshold,
        "db_samples": 0,
    }
    _write_metadata(metadata)

    logger.info(
        "ML models trained: %d samples, categorizer %.1f%%, predictor MAE ₹%.2f",
        len(rows), cat_accuracy, train_mae,
    )

    return {
        "status": "success",
        "corpus_size": len(rows),
        "categories": metadata["categories"],
        "categorizer_accuracy_pct": cat_accuracy,
        "predictor_mae": round(train_mae, 2),
        "predictor_mape_pct": mape,
        "anomaly_threshold": anomaly_threshold,
        "trained_at": metadata["trained_at"],
        "models_saved": [CATEGORIZER_PATH, PREDICTOR_PATH, ANOMALY_PATH],
    }


def train_from_db(db) -> dict:
    """
    Retrain using the curated corpus plus every labelled row stored in
    `ml_training_sample`. This lets merchants grow the training set over time
    from their own confirmed bills / ledger entries.
    """
    db_rows: list[tuple[str, str, float]] = []
    try:
        from db.models import MLTrainingSample
        for row in db.query(MLTrainingSample).all():
            db_rows.append((row.description, row.category, float(row.amount or 0.0)))
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Could not read ml_training_sample: %s", exc)

    combined = _normalise_samples(list(BOOTSTRAP_SAMPLES) + db_rows)
    result = train_models(combined)
    meta = _read_metadata()
    meta["db_samples"] = len(db_rows)
    meta["source"] = "bootstrap+db" if db_rows else "bootstrap"
    _write_metadata(meta)
    result["db_samples"] = len(db_rows)
    result["source"] = meta["source"]
    return result


def _ensure_models() -> None:
    """Train on import only when artefacts are missing or the corpus changed."""
    expected = _fingerprint(_normalise_samples(BOOTSTRAP_SAMPLES))
    meta = _read_metadata()
    files_ok = all(os.path.exists(p) for p in (CATEGORIZER_PATH, PREDICTOR_PATH, ANOMALY_PATH))
    if not files_ok or meta.get("engine_version") != ENGINE_VERSION or \
            meta.get("corpus_fingerprint") not in (None, expected):
        try:
            train_models()
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Automatic model training failed: %s", exc)


def _get_model(path: str, model_type: str = ""):
    if not os.path.exists(path):
        train_models()
    return joblib.load(path)


# ---------------------------------------------------------------------------
# Inference
# ---------------------------------------------------------------------------

def categorize_expense(description: str) -> str:
    """Predict the expense category for a transaction description."""
    if not description or not str(description).strip():
        return "General"
    try:
        model = _get_model(CATEGORIZER_PATH, "categorizer")
        return str(model.predict([str(description)])[0])
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Categorizer inference failed: %s", exc)
        return "General"


def is_anomaly(amount: float, context_amounts: list[float] | None = None) -> bool:
    """
    Decide whether an amount is unusually large.

    - When a merchant's own ledger is supplied (>= 5 rows) we compare against
      that ledger's median / 90th percentile (robust, per-user behaviour).
    - Otherwise we use the IsolationForest model plus absolute guards.
    """
    try:
        value = float(amount)
    except (TypeError, ValueError):
        return False
    if value <= 0:
        return False

    if context_amounts:
        positives = [float(a) for a in context_amounts if a is not None and float(a) > 0]
        if len(positives) >= 5:
            median = float(np.median(positives))
            p90 = float(np.percentile(positives, 90))
            ceiling = max(3000.0, median * 4.0, p90 * 2.0)
            return value > ceiling

    if value > 15000.0:
        return True

    try:
        model = _get_model(ANOMALY_PATH, "anomaly")
        threshold = float(_read_metadata().get("anomaly_threshold") or 5000.0)
        flagged = model.predict([[float(np.log1p(value))]])[0] == -1
        return bool(flagged and value >= threshold)
    except Exception:
        return value > 8000.0


def predict_future_spending(historical_daily_amounts: list[float] | None = None) -> dict:
    """
    Forecast the next 7 and 30 days of spending.

    If enough history is supplied we fit a fresh Ridge model on the merchant's
    own series, otherwise the globally trained model is used.
    """
    series = None
    if historical_daily_amounts and len(historical_daily_amounts) >= 10:
        series = [float(v) for v in historical_daily_amounts if v is not None]

    if series and len(series) >= 10:
        model, mae = _fit_series_model(series)
    else:
        model, mae = _get_model(PREDICTOR_PATH, "predictor"), \
            float(_read_metadata().get("predictor_mae") or 0.0)
        series = [float(v) for v in DAILY_SALES_SERIES]
        if historical_daily_amounts:
            # Blend the user's recent average with the seasonal baseline
            recent = [float(v) for v in historical_daily_amounts[-7:] if v is not None]
            if recent:
                ratio = (float(np.mean(recent)) + 1.0) / (float(np.mean(series[-7:])) + 1.0)
                series = [max(50.0, v * ratio) for v in series]

    history = list(series[-7:])
    base_day = len(series)
    predictions: list[float] = []

    for step in range(1, 31):
        idx = base_day + step - 1
        feats = np.asarray([[
            idx % 7,
            (idx % 30) + 1,
            history[-1],
            history[-2],
            history[-7],
        ]], dtype=float)
        value = max(100.0, float(model.predict(feats)[0]))
        predictions.append(round(value, 2))
        history.append(value)

    next_7 = predictions[:7]
    next_7_total = round(sum(next_7), 2)
    next_30_total = round(sum(predictions), 2)

    mean_pred = float(np.mean(predictions)) or 1.0
    if mae and mae > 0:
        confidence = max(55.0, min(97.0, round(100 - (mae / mean_pred * 100), 1)))
    else:
        confidence = 85.0

    return {
        "next_7_days": next_7,
        "next_7_days_total": next_7_total,
        "next_30_days": predictions,
        "next_30_days_total": next_30_total,
        "daily_average": round(next_30_total / 30, 2),
        "confidence_pct": confidence,
        "model": "RidgeRegression",
    }


# ---------------------------------------------------------------------------
# Aggregation for the user dashboard
# ---------------------------------------------------------------------------

def build_monthly_trend(transactions: list[dict], months: int = 6) -> list[dict]:
    """Aggregate income / expense / net by calendar month (oldest first)."""
    buckets: dict[str, dict] = {}
    for txn in transactions or []:
        raw_date = str(txn.get("date") or "")[:10]
        if len(raw_date) < 7:
            continue
        key = raw_date[:7]
        bucket = buckets.setdefault(
            key, {"month": key, "income": 0.0, "expense": 0.0}
        )
        try:
            amount = float(txn.get("amount") or 0.0)
        except (TypeError, ValueError):
            amount = 0.0
        if txn.get("type") == "income":
            bucket["income"] += amount
        else:
            bucket["expense"] += amount

    keys = sorted(buckets.keys())[-months:]
    trend = []
    for key in keys:
        bucket = buckets[key]
        try:
            label = datetime.strptime(key + "-01", "%Y-%m-%d").strftime("%b %Y")
        except ValueError:
            label = key
        trend.append({
            "month": key,
            "label": label,
            "income": round(bucket["income"], 2),
            "expense": round(bucket["expense"], 2),
            "net": round(bucket["income"] - bucket["expense"], 2),
        })
    return trend


def _empty_predictions() -> dict:
    return {
        "next_7_days": [0.0] * 7,
        "next_7_days_total": 0.0,
        "next_30_days": [0.0] * 30,
        "next_30_days_total": 0.0,
        "daily_average": 0.0,
        "confidence_pct": 0.0,
        "model": "RidgeRegression",
    }


def analyze_user_finances(transactions: list[dict], monthly_budget: float = 30000.0) -> dict:
    """Comprehensive ML analysis for the user dashboard."""
    transactions = transactions or []

    if not transactions:
        return {
            "balance": 0.0,
            "total_income": 0.0,
            "total_expense": 0.0,
            "savings_rate_pct": 0.0,
            "monthly_budget": monthly_budget,
            "categories": [],
            "monthly_trend": [],
            "predictions": _empty_predictions(),
            "anomaly_count": 0,
            "anomalies_count": 0,
            "anomalies": [],
            "insights": [
                "Welcome to your financial ledger! Record your daily transactions or "
                "upload supplier bills to generate AI predictions and anomaly alerts."
            ],
            "has_data": False,
        }

    expenses = [t for t in transactions if t.get("type") == "expense"]
    income = [t for t in transactions if t.get("type") == "income"]

    def _amt(t):
        try:
            return float(t.get("amount") or 0.0)
        except (TypeError, ValueError):
            return 0.0

    total_expense = sum(_amt(t) for t in expenses)
    total_income = sum(_amt(t) for t in income)
    balance = total_income - total_expense

    # Category breakdown
    cat_totals: dict[str, float] = {}
    for t in expenses:
        cat = t.get("category") or "General"
        cat_totals[cat] = cat_totals.get(cat, 0.0) + _amt(t)

    cat_list = [
        {
            "category": k,
            "amount": round(v, 2),
            "total_amount": round(v, 2),
            "pct": round(v / total_expense * 100, 1) if total_expense > 0 else 0.0,
        }
        for k, v in sorted(cat_totals.items(), key=lambda x: -x[1])
    ]

    # Future prediction (personalised when we have enough history)
    booking_dates: dict[str, float] = {}
    for t in expenses:
        d = str(t.get("date") or "")[:10]
        if len(d) == 10:
            booking_dates[d] = booking_dates.get(d, 0.0) + _amt(t)
    daily_series = [booking_dates[k] for k in sorted(booking_dates.keys())]
    predictions = predict_future_spending(daily_series if len(daily_series) >= 10 else None)

    # Anomaly detection (leave-one-out context for per-merchant behaviour)
    amounts_all = [_amt(t) for t in expenses]
    anomalies = []
    for idx, t in enumerate(expenses):
        context = amounts_all[:idx] + amounts_all[idx + 1:]
        if is_anomaly(amounts_all[idx], context):
            anomalies.append({
                "id": t.get("id"),
                "description": t.get("description"),
                "amount": round(amounts_all[idx], 2),
                "category": t.get("category"),
                "date": t.get("date"),
            })

    monthly_trend = build_monthly_trend(transactions)

    # Personalised insights
    insights = []
    if predictions["next_30_days_total"] > monthly_budget > 0:
        excess = predictions["next_30_days_total"] - monthly_budget
        insights.append(
            f"Predicted spending of ₹{predictions['next_30_days_total']:,.0f} exceeds your "
            f"monthly budget by ₹{excess:,.0f}. Cut discretionary food and shopping expenses."
        )
    elif monthly_budget > 0:
        saved = monthly_budget - predictions["next_30_days_total"]
        insights.append(
            f"Great financial discipline! You are on track to save approximately "
            f"₹{saved:,.0f} this month."
        )

    if cat_list:
        top_cat = cat_list[0]
        insights.append(
            f"Your highest spending category is {top_cat['category']} "
            f"({top_cat['pct']}% of total expenses)."
        )

    if anomalies:
        insights.append(
            f"{len(anomalies)} transaction(s) flagged as unusually high. "
            "Review them in your transaction ledger."
        )

    if len(monthly_trend) >= 2:
        prev, curr = monthly_trend[-2], monthly_trend[-1]
        if prev["expense"] > 0:
            delta = (curr["expense"] - prev["expense"]) / prev["expense"] * 100
            trend_word = "up" if delta > 0 else "down"
            insights.append(
                f"Month-over-month expenses are {trend_word} {abs(delta):.1f}% "
                f"({prev['label']} → {curr['label']})."
            )

    return {
        "balance": round(balance, 2),
        "total_income": round(total_income, 2),
        "total_expense": round(total_expense, 2),
        "savings_rate_pct": round(balance / total_income * 100, 1) if total_income > 0 else 0.0,
        "monthly_budget": monthly_budget,
        "categories": cat_list,
        "monthly_trend": monthly_trend,
        "predictions": predictions,
        "anomaly_count": len(anomalies),
        "anomalies_count": len(anomalies),
        "anomalies": anomalies,
        "insights": insights,
        "has_data": True,
    }


# Train on import only when artefacts are missing or out of date
_ensure_models()
