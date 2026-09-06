-- Persist share + research id on orders (IC regenerate / email links)
-- Safe to re-run.

ALTER TABLE orders ADD COLUMN IF NOT EXISTS share_url TEXT;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS research_id TEXT;

CREATE INDEX IF NOT EXISTS idx_orders_research_id
  ON orders (research_id)
  WHERE research_id IS NOT NULL;
