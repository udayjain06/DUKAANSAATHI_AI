"""
DukaanSaathi AI — Database models (SQLAlchemy)
"""
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Date,
    ForeignKey, Text, JSON
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def utc_now():
    """Return timezone-naive UTC datetime for clean DB compatibility."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class UserProfile(Base):
    __tablename__ = "user_profile"
    id = Column(String(80), primary_key=True, index=True)  # Supabase UUID or local user ID
    email = Column(String(120), unique=True, index=True)
    password_hash = Column(String(255), nullable=True)
    full_name = Column(String(120), default="")
    balance = Column(Float, default=0.0)
    language = Column(String(10), default="en")  # en | hi
    theme = Column(String(10), default="dark")    # light | dark
    monthly_budget = Column(Float, default=30000.0)
    is_demo = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)

    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    merchant = relationship("Merchant", back_populates="user", uselist=False, cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessage", back_populates="user", cascade="all, delete-orphan")


class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(String(80), primary_key=True, index=True)
    user_id = Column(String(80), ForeignKey("user_profile.id"), nullable=False, index=True)
    type = Column(String(20), default="expense")  # income | expense
    category = Column(String(60), default="General")
    amount = Column(Float, nullable=False)
    description = Column(String(255), default="")
    date = Column(Date, nullable=False, index=True)
    is_anomaly = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)

    user = relationship("UserProfile", back_populates="transactions")


class Merchant(Base):
    __tablename__ = "merchant"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(80), ForeignKey("user_profile.id"), nullable=True, index=True)
    name = Column(String(120), default="Demo Shop")
    shop_type = Column(String(60), default="kirana")  # kirana | bakery
    min_margin_pct = Column(Float, default=15.0)
    language = Column(String(10), default="hi")       # hi | en
    risk_budget_inr = Column(Float, default=400.0)
    phone = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=utc_now)

    user = relationship("UserProfile", back_populates="merchant")
    products = relationship("Product", back_populates="merchant", cascade="all, delete-orphan")
    sales = relationship("SalesDaily", back_populates="merchant", cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="merchant", cascade="all, delete-orphan")
    payment_orders = relationship("PaymentOrder", back_populates="merchant", cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessage", back_populates="merchant", cascade="all, delete-orphan")


class Product(Base):
    __tablename__ = "product"
    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(Integer, ForeignKey("merchant.id"), nullable=False)
    name = Column(String(120), nullable=False)
    category = Column(String(60), default="general")
    sell_price = Column(Float, nullable=False)
    cost_price = Column(Float, nullable=True)
    cost_source = Column(String(20), default="manual")  # bill | manual
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)

    merchant = relationship("Merchant", back_populates="products")
    sales_product = relationship("SalesProductDaily", back_populates="product")


class SalesDaily(Base):
    __tablename__ = "sales_daily"
    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(Integer, ForeignKey("merchant.id"), nullable=False)
    date = Column(Date, nullable=False, index=True)
    weekday = Column(String(10), nullable=False)  # Monday … Sunday
    total_amount = Column(Float, default=0.0)
    txn_count = Column(Integer, default=0)
    is_synthetic = Column(Boolean, default=True)

    merchant = relationship("Merchant", back_populates="sales")


class SalesProductDaily(Base):
    __tablename__ = "sales_product_daily"
    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(Integer, ForeignKey("merchant.id"), nullable=False)
    date = Column(Date, nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("product.id"), nullable=False)
    units = Column(Integer, default=0)
    revenue = Column(Float, default=0.0)
    is_synthetic = Column(Boolean, default=True)

    product = relationship("Product", back_populates="sales_product")


class BillItem(Base):
    __tablename__ = "bill_item"
    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(Integer, ForeignKey("merchant.id"), nullable=False)
    bill_id = Column(Integer, ForeignKey("bill.id"), nullable=True, index=True)
    bill_ref = Column(String(60), nullable=True)
    product_name = Column(String(120), nullable=False)
    cost_price = Column(Float, nullable=False)
    quantity = Column(Float, default=1.0)
    unit = Column(String(20), default="unit")
    confirmed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)


class Recommendation(Base):
    __tablename__ = "recommendation"
    id = Column(String(40), primary_key=True, index=True)
    merchant_id = Column(Integer, ForeignKey("merchant.id"), nullable=False)
    weak_day = Column(String(10))
    dip_pct = Column(Float)
    offer_json = Column(JSON)
    margin_json = Column(JSON)
    risk_json = Column(JSON)
    explanation_json = Column(JSON)
    status = Column(String(20), default="pending")  # pending | approved | modified | rejected
    data_label = Column(String(20), default="synthetic")
    created_at = Column(DateTime, default=utc_now)
    decided_at = Column(DateTime, nullable=True)
    modified_offer_json = Column(JSON, nullable=True)

    merchant = relationship("Merchant", back_populates="recommendations")
    offers = relationship("Offer", back_populates="recommendation")


class Offer(Base):
    __tablename__ = "offer"
    id = Column(String(40), primary_key=True, index=True)
    recommendation_id = Column(String(40), ForeignKey("recommendation.id"))
    merchant_id = Column(Integer, ForeignKey("merchant.id"), nullable=False)
    copy_json = Column(JSON)   # WhatsApp / poster text
    poster_json = Column(JSON, nullable=True)
    valid_from = Column(Date, nullable=True)
    valid_to = Column(Date, nullable=True)
    units_cap = Column(Integer, nullable=True)
    units_redeemed = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)

    recommendation = relationship("Recommendation", back_populates="offers")
    experiments = relationship("Experiment", back_populates="offer")


class Experiment(Base):
    __tablename__ = "experiment"
    id = Column(String(40), primary_key=True, index=True)
    offer_id = Column(String(40), ForeignKey("offer.id"))
    merchant_id = Column(Integer, ForeignKey("merchant.id"), nullable=False)
    treatment_product_ids = Column(JSON)   # list of product IDs
    control_product_ids = Column(JSON)     # list of product IDs
    before_period_json = Column(JSON)      # {start, end, units, revenue}
    after_period_json = Column(JSON, nullable=True)
    net_lift_pct = Column(Float, nullable=True)
    gp_change_inr = Column(Float, nullable=True)
    is_simulated = Column(Boolean, default=True)
    data_label = Column(String(20), default="synthetic")
    created_at = Column(DateTime, default=utc_now)

    offer = relationship("Offer", back_populates="experiments")


class PaymentOrder(Base):
    __tablename__ = "payment_order"
    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(Integer, ForeignKey("merchant.id"), nullable=False)
    order_id = Column(String(80), unique=True, nullable=False, index=True)
    txn_id = Column(String(80), nullable=True, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(5), default="INR")
    plan_name = Column(String(60), default="monthly")
    status = Column(String(30), default="PENDING")  # PENDING | SUCCESS | FAILED | CANCELLED
    paytm_response_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    verified_at = Column(DateTime, nullable=True)

    merchant = relationship("Merchant", back_populates="payment_orders")


class Bill(Base):
    """A supplier bill / invoice uploaded by a merchant (OCR source document)."""
    __tablename__ = "bill"
    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(Integer, ForeignKey("merchant.id"), nullable=False, index=True)
    bill_ref = Column(String(60), nullable=True, index=True)
    file_name = Column(String(255), nullable=True)
    file_type = Column(String(80), nullable=True)
    file_size = Column(Integer, default=0)
    ocr_engine = Column(String(40), default="none")
    ocr_confidence = Column(Float, nullable=True)
    raw_text = Column(Text, nullable=True)
    item_count = Column(Integer, default=0)
    total_amount = Column(Float, default=0.0)
    status = Column(String(20), default="extracted")  # extracted | confirmed | failed
    created_at = Column(DateTime, default=utc_now, index=True)


class MLTrainingSample(Base):
    """
    Labelled, real-world style training data for the ML engine.
    Seeded from Indian kirana / bakery / household transaction descriptions.
    Rows are never exposed across merchants — training uses this shared,
    anonymised corpus (description, category, amount only).
    """
    __tablename__ = "ml_training_sample"
    id = Column(Integer, primary_key=True, index=True)
    description = Column(String(255), nullable=False)
    category = Column(String(60), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    source = Column(String(30), default="seed")  # seed | merchant | ledger
    created_at = Column(DateTime, default=utc_now)


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(String(80), primary_key=True, index=True)
    user_id = Column(String(80), ForeignKey("user_profile.id"), nullable=False, index=True)
    merchant_id = Column(Integer, ForeignKey("merchant.id"), nullable=True, index=True)
    sender = Column(String(20), nullable=False)  # 'user' | 'ai'
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utc_now, index=True)

    user = relationship("UserProfile", back_populates="chat_messages")
    merchant = relationship("Merchant", back_populates="chat_messages")
