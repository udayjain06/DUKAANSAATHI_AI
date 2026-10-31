"""
Real-world style training corpus for DukaanSaathi AI.

These are hand-curated transaction descriptions that mirror what Indian
kirana stores, bakeries and small retailers actually record in their bahi-khata
(ledger) or see on supplier bills. They teach the ML models:

  1. Expense auto-categorisation (TF-IDF + LogisticRegression)
  2. Anomaly detection (IsolationForest on realistic amount ranges)
  3. Spending trend prediction (Ridge regression on realistic daily series)

The corpus is seeded into the `ml_training_sample` table so merchants can
retrain models from the database instead of hard-coded lists.
"""
from __future__ import annotations

# (description, category, typical_amount_inr)
# Amounts are realistic 2024-2026 Indian small-business figures.
REAL_LIFE_SAMPLES: list[tuple[str, str, float]] = [
    # ── Groceries / wholesale staples ──────────────────────────────────────
    ("atta wheat flour 10kg bag wholesale", "Groceries", 420.0),
    ("chawal basmati rice 25kg bori", "Groceries", 1850.0),
    ("toor dal 5kg wholesale packet", "Groceries", 780.0),
    ("chana dal 5kg", "Groceries", 520.0),
    ("moong dal 2kg", "Groceries", 290.0),
    ("refined sunflower oil 15 litre tin", "Groceries", 1980.0),
    ("mustard oil 5 litre jar", "Groceries", 720.0),
    ("sugar 50kg bori mill rate", "Groceries", 2250.0),
    ("jaggery gur 10kg", "Groceries", 480.0),
    ("tea leaves 5kg wholesale", "Groceries", 1450.0),
    ("milk powder 1kg pack", "Groceries", 410.0),
    ("salt 1kg 24 packet bundle", "Groceries", 300.0),
    ("turmeric powder 1kg", "Groceries", 260.0),
    ("red chilli powder 1kg", "Groceries", 340.0),
    ("garam masala 500g", "Groceries", 180.0),
    ("besan 2kg", "Groceries", 190.0),
    ("sooji rava 1kg", "Groceries", 75.0),
    ("poha 1kg", "Groceries", 65.0),
    ("maida 5kg bakery supply", "Groceries", 240.0),
    ("baking powder 500g", "Groceries", 130.0),
    ("dry fruits kaju 500g", "Groceries", 560.0),
    ("kishmish raisins 1kg", "Groceries", 320.0),
    ("peanuts 2kg", "Groceries", 260.0),
    ("papad 1kg packet", "Groceries", 160.0),
    ("ghee 1 litre tin", "Groceries", 620.0),
    ("paneer 1kg dairy delivery", "Groceries", 380.0),
    ("curd dahi 5kg bucket", "Groceries", 240.0),
    ("butter 500g amul", "Groceries", 290.0),
    ("eggs 30 tray wholesale", "Groceries", 210.0),
    ("onion 25kg bori mandi", "Groceries", 750.0),
    ("potato 25kg bori", "Groceries", 600.0),
    ("tomato 10kg crate", "Groceries", 280.0),
    ("green vegetables daily mandi", "Groceries", 340.0),
    ("fruits apple banana crate", "Groceries", 890.0),
    ("bread pav 50 packet bakery", "Groceries", 400.0),

    # ── Store supplies / packaging ─────────────────────────────────────────
    ("polythene carry bags 5kg bundle", "Supplies", 480.0),
    ("paper bags printed 1000 pcs", "Supplies", 1250.0),
    ("billing roll thermal paper", "Supplies", 360.0),
    ("packing tape 12 rolls", "Supplies", 240.0),
    ("carton boxes 50 pcs", "Supplies", 750.0),
    ("weighing scale battery cells", "Supplies", 120.0),
    ("cleaning phenyl 5 litre", "Supplies", 280.0),
    ("garbage bags roll", "Supplies", 90.0),
    ("shop broom and wiper", "Supplies", 210.0),
    ("led bulb replacement shop", "Supplies", 180.0),
    ("price tag stickers roll", "Supplies", 150.0),
    ("stapler pins and stationery", "Supplies", 95.0),
    ("display rack purchase", "Supplies", 2600.0),
    ("freezer repair technician", "Supplies", 1450.0),
    ("generator diesel refill", "Supplies", 900.0),
    ("delivery boy petrol reimbursement", "Supplies", 260.0),
    ("shop rent monthly", "Rent", 12000.0),
    ("godown rent warehouse", "Rent", 6500.0),
    ("shop electricity bill", "Utilities", 2450.0),
    ("water tanker supply", "Utilities", 600.0),
    ("broadband internet recharge", "Utilities", 799.0),
    ("mobile recharge jio prepaid", "Utilities", 299.0),
    ("lpg cylinder commercial refill", "Utilities", 1850.0),
    ("municipal waste collection fee", "Utilities", 350.0),
    ("gst filing accountant fee", "Utilities", 1500.0),
    ("shop insurance premium", "Utilities", 2400.0),
    ("staff salary monthly payment", "Salary", 15000.0),
    ("helper wages weekly", "Salary", 3500.0),
    ("delivery boy salary", "Salary", 9000.0),
    ("overtime payment festival season", "Salary", 2200.0),
    ("bonus diwali staff", "Salary", 5000.0),
    ("sales income counter collection", "Salary", 18000.0),
    ("upi settlement received", "Salary", 12400.0),
    ("paytm qr collection daily", "Salary", 8600.0),
    ("wholesale customer payment received", "Salary", 22000.0),

    # ── Food / staff meals / personal ──────────────────────────────────────
    ("staff lunch tiffin service", "Food", 480.0),
    ("chai snacks for shop staff", "Food", 160.0),
    ("swiggy dinner order", "Food", 420.0),
    ("zomato lunch delivery", "Food", 380.0),
    ("haldiram sweets festival box", "Food", 650.0),
    ("dhaba lunch with supplier", "Food", 720.0),
    ("samosa chai evening", "Food", 80.0),
    ("birthday cake for staff", "Food", 550.0),

    # ── Travel / transport ──────────────────────────────────────────────────
    ("tempo transport goods from mandi", "Travel", 1800.0),
    ("auto rickshaw delivery charges", "Travel", 220.0),
    ("petrol bike delivery", "Travel", 350.0),
    ("diesel tempo refill", "Travel", 2100.0),
    ("train ticket wholesale market trip", "Travel", 640.0),
    ("bus fare supplier visit", "Travel", 180.0),
    ("toll fastag recharge", "Travel", 500.0),
    ("parking charges market", "Travel", 60.0),
    ("courier delivery charges", "Travel", 320.0),

    # ── Shopping / equipment ────────────────────────────────────────────────
    ("mobile phone for billing use", "Shopping", 12999.0),
    ("barcode scanner purchase", "Shopping", 2400.0),
    ("printer cartridge refill", "Shopping", 850.0),
    ("cctv camera installation", "Shopping", 6800.0),
    ("plastic crates for storage 10 pcs", "Shopping", 1800.0),
    ("steel almirah shop", "Shopping", 9500.0),
    ("fan for shop summer", "Shopping", 2200.0),

    # ── Healthcare ──────────────────────────────────────────────────────────
    ("medical store medicine fever", "Healthcare", 460.0),
    ("doctor consultation clinic", "Healthcare", 500.0),
    ("blood test lab checkup", "Healthcare", 900.0),
    ("staff health insurance premium", "Healthcare", 3200.0),
    ("spectacles eye checkup", "Healthcare", 1500.0),

    # ── Entertainment / marketing ──────────────────────────────────────────
    ("whatsapp business api recharge", "Entertainment", 999.0),
    ("instagram ad promotion shop", "Entertainment", 1500.0),
    ("printing pamphlet offer 1000 pcs", "Entertainment", 1800.0),
    ("banner flex printing shop", "Entertainment", 1200.0),
    ("festival decoration lights", "Entertainment", 950.0),
    ("netflix subscription family", "Entertainment", 649.0),
    ("movie tickets family outing", "Entertainment", 760.0),
    ("cricket match tickets", "Entertainment", 1400.0),
    ("music system bluetooth speaker", "Entertainment", 2200.0),

    # ── Bakery-specific ─────────────────────────────────────────────────────
    ("bakery cream and butter supply", "Groceries", 1650.0),
    ("chocolate compound 5kg", "Groceries", 1900.0),
    ("cake moulds aluminium", "Supplies", 780.0),
    ("icing sugar 5kg", "Groceries", 420.0),
    ("food colour and essence", "Supplies", 340.0),
    ("pastry boxes 200 pcs", "Supplies", 900.0),
    ("oven gas cylinder refill", "Utilities", 1450.0),
    ("bakery staff baker salary", "Salary", 18000.0),
    ("cake order advance received", "Salary", 2500.0),
    ("birthday cake delivery auto", "Travel", 180.0),

    # ── Everyday merchant expenses ─────────────────────────────────────────
    ("tea kettle and cups for shop", "Supplies", 640.0),
    ("water cooler servicing", "Supplies", 550.0),
    ("pest control shop treatment", "Supplies", 1200.0),
    ("shop shutter repair welding", "Supplies", 1400.0),
    ("signboard painting", "Supplies", 2500.0),
    ("google business verification", "Entertainment", 0.0),
    ("paytm soundbox rental", "Utilities", 125.0),
    ("pos machine rental fee", "Utilities", 350.0),
    ("upi transaction charges", "Utilities", 180.0),
    ("bank current account charges", "Utilities", 450.0),
    ("loan emi business", "Utilities", 7800.0),
    ("gst payment quarterly", "Utilities", 6200.0),
    ("income tax advance", "Utilities", 5000.0),
    ("fire safety certificate renewal", "Utilities", 1100.0),
    ("shop licence renewal fee", "Utilities", 2000.0),
]


def get_training_samples() -> list[dict]:
    """Return the corpus as dictionaries ready for DB insertion."""
    return [
        {"description": d, "category": c, "amount": a, "source": "seed"}
        for d, c, a in REAL_LIFE_SAMPLES
    ]


# Realistic daily sales series (INR) for a kirana store over ~12 weeks.
# Encodes: weekend lift, Monday dip, salary-week (1-7) uplift, festival spikes.
# These are used to bootstrap the spending predictor when the database is empty.
DAILY_SALES_SERIES: list[float] = [
    4200, 4380, 4510, 4020, 3860, 5120, 5410,   # week 1 (salary week)
    4750, 4610, 4890, 4320, 4100, 5630, 5210,
    4360, 4180, 4470, 3910, 3720, 4980, 5150,
    4590, 4420, 4680, 4150, 3980, 5320, 5480,
    3980, 3810, 4090, 3620, 3450, 4720, 4860,
    4480, 4320, 4570, 4060, 3890, 5180, 5340,
    6120, 5980, 6240, 5710, 5520, 6980, 7210,   # festival week
    4620, 4460, 4710, 4180, 4010, 5360, 5520,
    4390, 4230, 4480, 3960, 3790, 5090, 5260,
    4710, 4550, 4820, 4280, 4110, 5480, 5640,
    4150, 3990, 4260, 3770, 3610, 4920, 5070,
    4520, 4360, 4620, 4090, 3930, 5270, 5430,
]
