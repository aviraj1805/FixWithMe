-- Anonymous repair outcomes (R1). No names, contacts, locations or free text are stored.
create table public.outcomes (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  item text not null check (char_length(item) <= 64),
  kb_version text not null check (char_length(kb_version) <= 32),
  cause_id text not null check (char_length(cause_id) <= 64),
  procedure_id text not null check (char_length(procedure_id) <= 64),
  resolved boolean not null,
  answers jsonb not null default '{}'::jsonb
    check (jsonb_typeof(answers) = 'object' and pg_column_size(answers) < 2048),
  lang text not null check (lang in ('en', 'hi'))
);

comment on table public.outcomes is
  'Anonymous repair outcomes from Fix with Me. Write-only for the anon role; read via the dashboard or service role.';

alter table public.outcomes enable row level security;

-- The API inserts with the publishable (anon) key. There are no select/update/delete policies,
-- so outcomes cannot be read or changed with that key.
create policy "anon can insert outcomes"
  on public.outcomes for insert
  to anon
  with check (true);
