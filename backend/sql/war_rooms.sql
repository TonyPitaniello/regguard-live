-- Optional Supabase table for durable war-room comments (dual-write from war_room_store.py)
create table if not exists war_rooms (
  research_id text primary key,
  comments jsonb not null default '[]'::jsonb,
  write_token text not null default '',
  updated_at timestamptz
);
