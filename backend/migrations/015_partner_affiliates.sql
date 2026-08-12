-- Partner $79 tier + optional affiliates table
-- Safe to re-run.

ALTER TABLE orders DROP CONSTRAINT IF EXISTS orders_tier_check;
ALTER TABLE orders ADD CONSTRAINT orders_tier_check CHECK (
  tier IN (
    'free',
    'partner',
    'contractor_pro',
    'ic_consultant',
    'ic_project',
    'ic_annual',
    'sponsor'
  )
);

CREATE TABLE IF NOT EXISTS affiliates (
  code TEXT PRIMARY KEY,
  email TEXT NOT NULL,
  name TEXT,
  commission_rate NUMERIC DEFAULT 0.20,
  clicks INTEGER DEFAULT 0,
  active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  last_click_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS affiliate_commissions (
  id TEXT PRIMARY KEY,
  affiliate_code TEXT REFERENCES affiliates(code),
  affiliate_email TEXT,
  order_id TEXT,
  customer_email TEXT,
  tier TEXT,
  sale_amount_cents INTEGER,
  commission_cents INTEGER,
  commission_rate NUMERIC,
  paid BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  paid_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_affiliate_commissions_unpaid
  ON affiliate_commissions (paid)
  WHERE paid = FALSE;
