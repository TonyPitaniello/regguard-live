"""SQL for product_events (Supabase dual-write)."""
from __future__ import annotations

# create table if not exists product_events (
#   id uuid primary key default gen_random_uuid(),
#   ts timestamptz not null default now(),
#   event text not null,
#   research_id text,
#   zip text,
#   stamp_grade text,
#   stamp_fingerprint text,
#   channel text,
#   meta jsonb default '{}'::jsonb
# );
# create index if not exists product_events_ts_idx on product_events (ts desc);
# create index if not exists product_events_event_idx on product_events (event);
#
# RLS: deny anon/authenticated; service_role only.
# Run from SQL Editor.
# Note: create table is intentionally not inlined as a full migration — keep dual-write flexible.
