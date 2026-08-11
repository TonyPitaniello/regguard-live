-- Persist IC Project PDF metadata + analysis for regenerate-on-demand
-- Safe to re-run.

ALTER TABLE orders ADD COLUMN IF NOT EXISTS pdfs JSONB;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS analysis_json JSONB;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS address TEXT;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS download_token TEXT;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS pdf_status TEXT;

CREATE INDEX IF NOT EXISTS idx_orders_email_created
  ON orders (email, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_orders_download_token
  ON orders (download_token)
  WHERE download_token IS NOT NULL;
