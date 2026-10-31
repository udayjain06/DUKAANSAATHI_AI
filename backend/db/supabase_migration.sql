-- ==============================================================================
-- DukaanSaathi AI — Complete Supabase PostgreSQL Schema & Migration Script
-- Run this in the Supabase SQL Editor to apply or verify all tables and relations.
-- ==============================================================================

-- 1. User Profile Table
CREATE TABLE IF NOT EXISTS public.user_profile (
    id VARCHAR(80) PRIMARY KEY,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    full_name VARCHAR(120) DEFAULT '',
    balance DOUBLE PRECISION DEFAULT 0.0,
    language VARCHAR(10) DEFAULT 'hi',
    theme VARCHAR(10) DEFAULT 'dark',
    monthly_budget DOUBLE PRECISION DEFAULT 30000.0,
    is_demo BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc')
);

-- Ensure migration columns exist on legacy user_profile
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='user_profile' AND column_name='password_hash') THEN
        ALTER TABLE public.user_profile ADD COLUMN password_hash VARCHAR(255);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='user_profile' AND column_name='is_demo') THEN
        ALTER TABLE public.user_profile ADD COLUMN is_demo BOOLEAN DEFAULT FALSE;
    END IF;
END $$;

-- 2. Merchant / Shop Table (Linked to UserProfile)
CREATE TABLE IF NOT EXISTS public.merchant (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(80) REFERENCES public.user_profile(id) ON DELETE CASCADE,
    name VARCHAR(120) DEFAULT 'My Shop',
    shop_type VARCHAR(60) DEFAULT 'kirana',
    min_margin_pct DOUBLE PRECISION DEFAULT 15.0,
    language VARCHAR(10) DEFAULT 'hi',
    risk_budget_inr DOUBLE PRECISION DEFAULT 400.0,
    phone VARCHAR(20),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc')
);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='merchant' AND column_name='user_id') THEN
        ALTER TABLE public.merchant ADD COLUMN user_id VARCHAR(80) REFERENCES public.user_profile(id) ON DELETE CASCADE;
    END IF;
END $$;

-- 3. Product Catalog Table
CREATE TABLE IF NOT EXISTS public.product (
    id SERIAL PRIMARY KEY,
    merchant_id INTEGER NOT NULL REFERENCES public.merchant(id) ON DELETE CASCADE,
    name VARCHAR(120) NOT NULL,
    category VARCHAR(60) DEFAULT 'general',
    sell_price DOUBLE PRECISION NOT NULL,
    cost_price DOUBLE PRECISION,
    cost_source VARCHAR(20) DEFAULT 'manual',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc')
);

-- 4. Daily Sales Aggregations
CREATE TABLE IF NOT EXISTS public.sales_daily (
    id SERIAL PRIMARY KEY,
    merchant_id INTEGER NOT NULL REFERENCES public.merchant(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    weekday VARCHAR(10) NOT NULL,
    total_amount DOUBLE PRECISION DEFAULT 0.0,
    txn_count INTEGER DEFAULT 0,
    is_synthetic BOOLEAN DEFAULT FALSE
);

-- 5. Daily Product Sales Breakdown
CREATE TABLE IF NOT EXISTS public.sales_product_daily (
    id SERIAL PRIMARY KEY,
    merchant_id INTEGER NOT NULL REFERENCES public.merchant(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    product_id INTEGER NOT NULL REFERENCES public.product(id) ON DELETE CASCADE,
    units INTEGER DEFAULT 0,
    revenue DOUBLE PRECISION DEFAULT 0.0,
    is_synthetic BOOLEAN DEFAULT FALSE
);

-- 6. Supplier Bills and Invoices
CREATE TABLE IF NOT EXISTS public.bill_item (
    id SERIAL PRIMARY KEY,
    merchant_id INTEGER NOT NULL REFERENCES public.merchant(id) ON DELETE CASCADE,
    bill_ref VARCHAR(60),
    product_name VARCHAR(120) NOT NULL,
    cost_price DOUBLE PRECISION NOT NULL,
    quantity DOUBLE PRECISION DEFAULT 1.0,
    unit VARCHAR(20) DEFAULT 'unit',
    confirmed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc')
);

-- 7. Recommendations
CREATE TABLE IF NOT EXISTS public.recommendation (
    id VARCHAR(40) PRIMARY KEY,
    merchant_id INTEGER NOT NULL REFERENCES public.merchant(id) ON DELETE CASCADE,
    weak_day VARCHAR(10),
    dip_pct DOUBLE PRECISION,
    offer_json JSONB,
    margin_json JSONB,
    risk_json JSONB,
    explanation_json JSONB,
    status VARCHAR(20) DEFAULT 'pending',
    data_label VARCHAR(20) DEFAULT 'real',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc'),
    decided_at TIMESTAMP WITHOUT TIME ZONE,
    modified_offer_json JSONB
);

-- 8. Promotional Offers
CREATE TABLE IF NOT EXISTS public.offer (
    id VARCHAR(40) PRIMARY KEY,
    recommendation_id VARCHAR(40) REFERENCES public.recommendation(id) ON DELETE SET NULL,
    merchant_id INTEGER NOT NULL REFERENCES public.merchant(id) ON DELETE CASCADE,
    copy_json JSONB,
    poster_json JSONB,
    valid_from DATE,
    valid_to DATE,
    units_cap INTEGER,
    units_redeemed INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc')
);

-- 9. A/B Margin Experiments
CREATE TABLE IF NOT EXISTS public.experiment (
    id VARCHAR(40) PRIMARY KEY,
    offer_id VARCHAR(40) REFERENCES public.offer(id) ON DELETE SET NULL,
    merchant_id INTEGER NOT NULL REFERENCES public.merchant(id) ON DELETE CASCADE,
    treatment_product_ids JSONB,
    control_product_ids JSONB,
    before_period_json JSONB,
    after_period_json JSONB,
    net_lift_pct DOUBLE PRECISION,
    gp_change_inr DOUBLE PRECISION,
    is_simulated BOOLEAN DEFAULT TRUE,
    data_label VARCHAR(20) DEFAULT 'real',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc')
);

-- 10. Paytm Payment Orders
CREATE TABLE IF NOT EXISTS public.payment_order (
    id SERIAL PRIMARY KEY,
    merchant_id INTEGER NOT NULL REFERENCES public.merchant(id) ON DELETE CASCADE,
    order_id VARCHAR(80) UNIQUE NOT NULL,
    txn_id VARCHAR(80),
    amount DOUBLE PRECISION NOT NULL,
    currency VARCHAR(5) DEFAULT 'INR',
    plan_name VARCHAR(60) DEFAULT 'monthly',
    status VARCHAR(30) DEFAULT 'PENDING',
    paytm_response_json JSONB,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc'),
    verified_at TIMESTAMP WITHOUT TIME ZONE
);

-- 11. Personal & Shop Transaction Ledger
CREATE TABLE IF NOT EXISTS public.transactions (
    id VARCHAR(80) PRIMARY KEY,
    user_id VARCHAR(80) NOT NULL REFERENCES public.user_profile(id) ON DELETE CASCADE,
    type VARCHAR(20) DEFAULT 'expense',
    category VARCHAR(60) DEFAULT 'General',
    amount DOUBLE PRECISION NOT NULL,
    description VARCHAR(255) DEFAULT '',
    date DATE NOT NULL,
    is_anomaly BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc')
);

-- 12. Isolated AI Chat History
CREATE TABLE IF NOT EXISTS public.chat_messages (
    id VARCHAR(80) PRIMARY KEY,
    user_id VARCHAR(80) NOT NULL REFERENCES public.user_profile(id) ON DELETE CASCADE,
    merchant_id INTEGER REFERENCES public.merchant(id) ON DELETE CASCADE,
    sender VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc')
);

-- Indexes for Fast Query Performance
CREATE INDEX IF NOT EXISTS idx_merchant_user_id ON public.merchant(user_id);
CREATE INDEX IF NOT EXISTS idx_product_merchant_id ON public.product(merchant_id);
CREATE INDEX IF NOT EXISTS idx_sales_daily_merchant_date ON public.sales_daily(merchant_id, date);
CREATE INDEX IF NOT EXISTS idx_bill_item_merchant_id ON public.bill_item(merchant_id);
CREATE INDEX IF NOT EXISTS idx_recommendation_merchant_id ON public.recommendation(merchant_id);
CREATE INDEX IF NOT EXISTS idx_offer_merchant_id ON public.offer(merchant_id);
CREATE INDEX IF NOT EXISTS idx_transactions_user_date ON public.transactions(user_id, date);
CREATE INDEX IF NOT EXISTS idx_chat_messages_user_id ON public.chat_messages(user_id);

