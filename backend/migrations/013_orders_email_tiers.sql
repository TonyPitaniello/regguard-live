-- Expand orders for tier checkouts (Contractor Pro / IC Project) + email lookup
-- Safe to re-run.

ALTER TABLE orders ADD COLUMN IF NOT EXISTS email TEXT;

-- Allow app tier names in addition to legacy ic_consultant
ALTER TABLE orders DROP CONSTRAINT IF EXISTS orders_tier_check;
ALTER TABLE orders ADD CONSTRAINT orders_tier_check CHECK (
  tier IN (
    'free',
    'contractor_pro',
    'ic_consultant',
    'ic_project',
    'ic_annual',
    'sponsor'
  )
);

-- user_id can be a synthetic UUID derived from email for guest checkout
ALTER TABLE orders ALTER COLUMN user_id DROP NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_stripe_session_unique
  ON orders (stripe_session_id)
  WHERE stripe_session_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_orders_email ON orders (email);
