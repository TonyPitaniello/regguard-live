-- Durable war rooms + stamp snapshot for dispute proof
-- Run in Supabase SQL editor. Safe to re-run.

create table if not exists war_rooms (
  research_id text primary key,
  comments jsonb not null default '[]'::jsonb,
  write_token text not null default '',
  stamp_snapshot jsonb not null default '{}'::jsonb,
  updated_at timestamptz
);

alter table war_rooms
  add column if not exists stamp_snapshot jsonb not null default '{}'::jsonb;

-- Lock down: no anon/authenticated direct access; service role (backend) bypasses RLS.
alter table war_rooms enable row level security;

drop policy if exists war_rooms_deny_all on war_rooms;
create policy war_rooms_deny_all on war_rooms
  for all
  using (false)
  with check (false);

-- Optional: allow service_role explicitly (usually not required — service_role bypasses RLS)
-- grant all on war_rooms to service_role;

comment on table war_rooms is 'RegGuard deal-team war room; writes only via backend service role';
comment on column war_rooms.stamp_snapshot is 'Frozen RegGuard stamp grade+fingerprint at attach time';
