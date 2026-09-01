-- Quick one-liner if the advisory only names war_rooms:
-- Supabase → SQL Editor → Run

alter table public.war_rooms enable row level security;

drop policy if exists war_rooms_deny_all on public.war_rooms;
create policy war_rooms_deny_all on public.war_rooms
  for all
  to anon, authenticated
  using (false)
  with check (false);

revoke all on table public.war_rooms from anon, authenticated;
grant all on table public.war_rooms to service_role;
