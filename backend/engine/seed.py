"""
Synthetic data generator — seed.py
8 weeks of realistic daily sales for kirana / bakery merchants.
random.seed(42) ensures reproducible demo data.
"""
import random
import datetime
from sqlalchemy.orm import Session
from db.models import Merchant, Product, SalesDaily, SalesProductDaily

random.seed(42)

WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# Base daily revenue per shop type (INR)
SHOP_PROFILES = {
    "kirana": {"base": 4500, "products": [
        {"name": "Parle-G Biscuits", "category": "snacks", "sell_price": 10, "cost_price": 7},
        {"name": "Maggi Noodles", "category": "food", "sell_price": 14, "cost_price": 10},
        {"name": "Amul Milk 500ml", "category": "dairy", "sell_price": 30, "cost_price": 24},
        {"name": "Tata Salt 1kg", "category": "grocery", "sell_price": 24, "cost_price": 18},
        {"name": "Chips (Lays)", "category": "snacks", "sell_price": 20, "cost_price": 14},
        {"name": "Cold Drink (Pepsi 250ml)", "category": "beverages", "sell_price": 20, "cost_price": 14},
        {"name": "Surf Excel 500g", "category": "household", "sell_price": 90, "cost_price": 70},
        {"name": "Colgate 100g", "category": "personal_care", "sell_price": 49, "cost_price": 36},
    ]},
    "bakery": {"base": 3200, "products": [
        {"name": "Pav Bread", "category": "bread", "sell_price": 25, "cost_price": 16},
        {"name": "Chocolate Pastry", "category": "pastry", "sell_price": 60, "cost_price": 38},
        {"name": "Plain Cake", "category": "cake", "sell_price": 180, "cost_price": 110},
        {"name": "Samosa (2 pcs)", "category": "snacks", "sell_price": 20, "cost_price": 12},
        {"name": "Veg Puff", "category": "snacks", "sell_price": 18, "cost_price": 11},
        {"name": "Bread Loaf", "category": "bread", "sell_price": 40, "cost_price": 26},
        {"name": "Cookie Pack", "category": "cookies", "sell_price": 45, "cost_price": 28},
        {"name": "Cream Roll", "category": "pastry", "sell_price": 30, "cost_price": 18},
    ]},
}


def _daily_multiplier(date: datetime.date, weekday_idx: int) -> float:
    """Return a multiplier for the day based on patterns from the spec."""
    mult = 1.0
    # Monday dip: 12–18%
    if weekday_idx == 0:
        mult *= random.uniform(0.82, 0.88)
    # Weekend boost: Sat/Sun
    elif weekday_idx in (5, 6):
        mult *= random.uniform(1.10, 1.22)
    # Salary window 1–7: bump ~10–15%
    if 1 <= date.day <= 7:
        mult *= random.uniform(1.10, 1.15)
    # Small random noise ±7%
    mult *= random.uniform(0.93, 1.07)
    return mult


def seed_merchant(db: Session, shop_type: str = "kirana", merchant_id: int = 1) -> Merchant:
    """Create or return existing demo merchant assigned to the demo account."""
    from db.models import UserProfile
    from core.security import hash_password

    demo_user = db.query(UserProfile).filter(UserProfile.id == "demo-user-001").first()
    if not demo_user:
        demo_user = UserProfile(
            id="demo-user-001",
            email="demo@dukaansaathi.ai",
            password_hash=hash_password("Demo@123"),
            full_name="Demo Shopkeeper",
            balance=28450.0,
            monthly_budget=30000.0,
            language="hi",
            theme="dark",
            is_demo=True,
        )
        db.add(demo_user)
        db.flush()

    merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()
    if not merchant:
        merchant = Merchant(
            id=merchant_id,
            user_id=demo_user.id,
            name="Sharma General Store" if shop_type == "kirana" else "Sweet Treat Bakery",
            shop_type=shop_type,
            min_margin_pct=15.0,
            language="hi",
            risk_budget_inr=400.0,
            phone="9999999999",
        )
        db.add(merchant)
        db.commit()
        db.refresh(merchant)
    elif not merchant.user_id:
        merchant.user_id = demo_user.id
        db.commit()
        db.refresh(merchant)

    return merchant


def seed_products(db: Session, merchant: Merchant) -> list:
    """Create demo products if they don't exist."""
    existing = db.query(Product).filter(Product.merchant_id == merchant.id).count()
    if existing > 0:
        return db.query(Product).filter(Product.merchant_id == merchant.id).all()

    profile = SHOP_PROFILES.get(merchant.shop_type, SHOP_PROFILES["kirana"])
    products = []
    for p in profile["products"]:
        prod = Product(
            merchant_id=merchant.id,
            name=p["name"],
            category=p["category"],
            sell_price=p["sell_price"],
            cost_price=p["cost_price"],
            cost_source="bill",
        )
        db.add(prod)
        products.append(prod)
    db.commit()
    for p in products:
        db.refresh(p)
    return products


def seed_sales(db: Session, merchant: Merchant, products: list, weeks: int = 8):
    """Generate 8 weeks of synthetic daily sales. Idempotent."""
    existing = db.query(SalesDaily).filter(SalesDaily.merchant_id == merchant.id).count()
    if existing > 0:
        return

    profile = SHOP_PROFILES.get(merchant.shop_type, SHOP_PROFILES["kirana"])
    base = profile["base"]

    today = datetime.date.today()
    start_date = today - datetime.timedelta(weeks=weeks)

    current = start_date
    while current <= today:
        weekday_idx = current.weekday()  # 0=Mon … 6=Sun
        weekday_name = WEEKDAY_NAMES[weekday_idx]
        mult = _daily_multiplier(current, weekday_idx)
        day_amount = round(base * mult, 2)
        txn_count = random.randint(18, 55)

        sd = SalesDaily(
            merchant_id=merchant.id,
            date=current,
            weekday=weekday_name,
            total_amount=day_amount,
            txn_count=txn_count,
            is_synthetic=True,
        )
        db.add(sd)

        # Distribute revenue across products
        remaining = day_amount
        for i, prod in enumerate(products):
            if i == len(products) - 1:
                units = max(1, int(remaining / prod.sell_price))
                rev = round(units * prod.sell_price, 2)
            else:
                share = random.uniform(0.05, 0.20)
                rev = round(day_amount * share, 2)
                units = max(0, int(rev / prod.sell_price))
                remaining -= rev

            if units > 0:
                spd = SalesProductDaily(
                    merchant_id=merchant.id,
                    date=current,
                    product_id=prod.id,
                    units=units,
                    revenue=round(units * prod.sell_price, 2),
                    is_synthetic=True,
                )
                db.add(spd)

        current += datetime.timedelta(days=1)

    db.commit()


def run_seed(db: Session, shop_type: str = "kirana"):
    """Full seed: merchant + products + sales. Call this to reset demo data."""
    random.seed(42)
    merchant = seed_merchant(db, shop_type=shop_type, merchant_id=1)
    products = seed_products(db, merchant)
    seed_sales(db, merchant, products, weeks=8)
    seed_ml_training_samples(db)
    seed_demo_transactions(db, merchant)
    return merchant


# ---------------------------------------------------------------------------
# ML training corpus + realistic demo ledger
# ---------------------------------------------------------------------------

def seed_ml_training_samples(db: Session):
    """Copy the curated real-life corpus into `ml_training_sample`. Idempotent."""
    from db.models import MLTrainingSample
    from engine.training_data import get_training_samples

    try:
        existing = db.query(MLTrainingSample).count()
    except Exception:
        return 0
    if existing > 0:
        return existing

    rows = [
        MLTrainingSample(
            description=row["description"],
            category=row["category"],
            amount=row["amount"],
            source="seed",
        )
        for row in get_training_samples()
    ]
    db.add_all(rows)
    db.commit()
    return len(rows)


# Realistic merchant ledger for the demo account: two months of income and
# expenses so the dashboard, ML forecasts and chat all have real data.
DEMO_LEDGER = [
    # (days_ago, type, description, amount)
    (0, "expense", "tea and snacks for shop staff", 240.0),
    (1, "expense", "petrol bike for delivery", 350.0),
    (1, "income", "counter sales collection", 4850.0),
    (2, "expense", "Amul milk and curd supply", 1240.0),
    (2, "income", "UPI settlement received", 3620.0),
    (3, "expense", "polythene carry bags 5kg bundle", 480.0),
    (3, "income", "counter sales collection", 4120.0),
    (4, "expense", "wholesale atta and rice bori", 2870.0),
    (4, "income", "Paytm QR collection daily", 5240.0),
    (5, "expense", "shop electricity bill", 2450.0),
    (5, "income", "counter sales collection", 3980.0),
    (6, "expense", "tempo transport from mandi", 1800.0),
    (6, "income", "Sunday weekend sales", 6120.0),
    (8, "expense", "mobile recharge prepaid", 299.0),
    (9, "expense", "billing roll thermal paper", 360.0),
    (9, "income", "counter sales collection", 4410.0),
    (11, "expense", "staff salary monthly payment", 15000.0),
    (11, "income", "wholesale customer payment received", 22000.0),
    (13, "expense", "shop rent monthly", 12000.0),
    (15, "expense", "gst filing accountant fee", 1500.0),
    (16, "income", "counter sales collection", 4680.0),
    (19, "expense", "mustard oil 5 litre jar", 720.0),
    (22, "expense", "water tanker supply", 600.0),
    (24, "income", "UPI settlement received", 7420.0),
    (26, "expense", "sugar 50kg bori mill rate", 2250.0),
    (29, "expense", "broadband internet recharge", 799.0),
    (31, "income", "counter sales collection", 5120.0),
    (34, "expense", "LED bulbs and shop repairs", 640.0),
    (38, "expense", "festival decoration lights", 950.0),
    (41, "income", "festival week sales", 9210.0),
    (45, "expense", "loan EMI business", 7800.0),
    (49, "expense", "shop insurance premium", 2400.0),
    (52, "income", "counter sales collection", 4560.0),
    (58, "expense", "display rack purchase", 2600.0),
    (61, "income", "UPI settlement received", 6840.0),
]


def seed_demo_transactions(db: Session, merchant: Merchant):
    """Add a realistic 2-month ledger for the demo account. Idempotent."""
    from db.models import Transaction
    from engine.ml_engine import categorize_expense

    user_id = merchant.user_id
    if not user_id:
        return 0
    existing = db.query(Transaction).filter(Transaction.user_id == user_id).count()
    if existing > 0:
        return existing

    today = datetime.date.today()
    created = 0
    for days_ago, txn_type, description, amount in DEMO_LEDGER:
        db.add(Transaction(
            id=f"tx_demo_{created + 1:03d}",
            user_id=user_id,
            type=txn_type,
            category="Salary" if txn_type == "income" else categorize_expense(description),
            amount=float(amount),
            description=description,
            date=today - datetime.timedelta(days=days_ago),
            is_anomaly=amount >= 15000,
        ))
        created += 1
    db.commit()
    return created


def ensure_demo_data(db: Session):
    """Idempotently make sure demo data, the ML corpus and demo ledger exist."""
    from db.models import SalesDaily

    if db.query(SalesDaily).count() == 0:
        run_seed(db, shop_type="kirana")
        return

    merchant = db.query(Merchant).filter(Merchant.id == 1).first()
    if not merchant:
        merchant = seed_merchant(db, shop_type="kirana", merchant_id=1)
    seed_ml_training_samples(db)
    seed_demo_transactions(db, merchant)


