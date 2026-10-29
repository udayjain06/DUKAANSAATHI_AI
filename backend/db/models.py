"""
DukaanSaathi AI — Database models (SQLAlchemy)
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Date,
    ForeignKey, Text, JSON
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Merchant(Base):
    __tablename__ = "merchant"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), default="Demo Shop")
    shop_type = Column(String(60), default="kirana")  # kirana | bakery
    min_margin_pct = Column(Float, default=15.0)
    language = Column(String(10), default="hi")       # hi | en
    risk_budget_inr = Column(Float, default=400.0)
    phone = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    products = relationship("Product", back_populates="merchant")
    sales = relationship("SalesDaily", back_populates="merchant")
    recommendations = relationship("Recommendation", back_populates="merchant")
    payment_orders = relationship("PaymentOrder", back_populates="merchant")


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
    created_at = Column(DateTime, default=datetime.utcnow)

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
    bill_ref = Column(String(60), nullable=True)
    product_name = Column(String(120), nullable=False)
    cost_price = Column(Float, nullable=False)
    quantity = Column(Float, default=1.0)
    unit = Column(String(20), default="unit")
    confirmed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


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
    created_at = Column(DateTime, default=datetime.utcnow)
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
    created_at = Column(DateTime, default=datetime.utcnow)

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
    created_at = Column(DateTime, default=datetime.utcnow)

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
    created_at = Column(DateTime, default=datetime.utcnow)
    verified_at = Column(DateTime, nullable=True)

    merchant = relationship("Merchant", back_populates="payment_orders")

