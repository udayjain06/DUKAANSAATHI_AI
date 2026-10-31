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
    return merchant

