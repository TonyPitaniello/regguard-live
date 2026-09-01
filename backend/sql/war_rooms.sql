-- Fix Supabase advisory: rls_disabled_in_public (CRITICAL)
-- Project: Reg Guard (cukshjdvlydzxiqnjdaw)
--
-- Run in: Supabase Dashboard → SQL Editor → New query → Paste → Run
-- Safe to re-run.
--
-- Backend must use the service_role key (SUPABASE_KEY on Render), which bypasses RLS.
-- Never put the service_role key in the frontend / Vercel anon client.

-- ---------------------------------------------------------------------------
-- 1) war_rooms — durable deal-team comments (backend dual-write only)
-- ---------------------------------------------------------------------------
create table if not exists public.war_rooms (
  research_id text primary key,
  comments jsonb not null default '[]'::jsonb,
  write_token text not null default '',
  stamp_snapshot jsonb not null default '{}'::jsonb,
  updated_at timestamptz
);

alter table public.war_rooms
  add column if not exists stamp_snapshot jsonb not null default '{}'::jsonb;

alter table public.war_rooms enable row level security;

-- Deny all access for roles subject to RLS (anon / authenticated).
drop policy if exists war_rooms_deny_all on public.war_rooms;
create policy war_rooms_deny_all on public.war_rooms
  for all
  to anon, authenticated
  using (false)
  with check (false);

-- Belt-and-suspenders: revoke direct table privileges from public API roles.
revoke all on table public.war_rooms from anon, authenticated;
grant all on table public.war_rooms to service_role;

comment on table public.war_rooms is
  'RegGuard war room; client access only via FastAPI using service_role';

-- ---------------------------------------------------------------------------
-- 2) Enable RLS on ANY other public tables that still have it off
--    (clears remaining rls_disabled_in_public advisories).
--    With RLS on and no permissive policies, anon/authenticated see nothing.
--    service_role continues to work from the API.
-- ---------------------------------------------------------------------------
do $$
declare
  r record;
begin
  for r in
    select n.nspname as schemaname, c.relname as tablename
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace
    where c.relkind = 'r'
      and n.nspname = 'public'
      and c.relrowsecurity = false
      and c.relname not like 'pg_%'
  loop
    execute format('alter table %I.%I enable row level security', r.schemaname, r.tablename);
    raise notice 'Enabled RLS on %.%', r.schemaname, r.tablename;
  end loop;
end $$;

-- ---------------------------------------------------------------------------
-- 3) Verify — should return zero rows after this script
-- ---------------------------------------------------------------------------
-- select schemaname, tablename
-- from pg_tables t
-- join pg_class c on c.relname = t.tablename
-- join pg_namespace n on n.oid = c.relnamespace and n.nspname = t.schemaname
-- where t.schemaname = 'public' and c.relrowsecurity = false;

select
  c.relname as table_name,
  c.relrowsecurity as rls_enabled
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public'
  and c.relkind = 'r'
order by c.relname;
