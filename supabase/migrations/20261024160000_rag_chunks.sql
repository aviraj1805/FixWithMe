-- R3: retrieval corpus (curated KB + Wikipedia) with hybrid search.
create extension if not exists vector with schema extensions;
create extension if not exists pgroonga with schema extensions;

-- Ingest tokens: only SHA-256 hashes are stored; the token itself lives in the operator's .env.
create schema if not exists private;
create table if not exists private.ingest_tokens (
  token_hash text primary key,
  created_at timestamptz not null default now()
);
insert into private.ingest_tokens (token_hash)
values ('ff6b5645f5a7a1d095a10198fdb4be83b70856ea04e2e3efce25829fc95ea003')
on conflict do nothing;

create table public.chunks (
  id text primary key,
  source_type text not null check (source_type in ('kb', 'wikipedia', 'manual')),
  title text not null,
  url text,
  license text not null,
  lang text not null check (lang in ('en', 'hi')),
  product text,
  safety_level int,
  content text not null,
  embedding extensions.vector(768) not null,
  updated_at timestamptz not null default now()
);
comment on table public.chunks is
  'Retrieval passages. Not readable with the API keys (RLS, no policies); search only via search_chunks().';

alter table public.chunks enable row level security;

create index chunks_embedding_hnsw on public.chunks using hnsw (embedding extensions.vector_cosine_ops);
create index chunks_content_pgroonga on public.chunks using pgroonga (content);
create index chunks_product on public.chunks (product);

-- Candidates from vector search and from PGroonga full-text search (multilingual, incl.
-- Devanagari). The API fuses the two rankings (reciprocal rank fusion).
create or replace function public.search_chunks(
  query_text text,
  query_embedding extensions.vector(768),
  product_filter text default null,
  pool int default 30
)
returns table (
  id text, title text, url text, license text, source_type text, lang text, product text,
  safety_level int, content text, vec_rank int, kw_rank int
)
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
  q text;
begin
  -- pgroonga_score() is only filled in by an index scan; the table is small enough that the
  -- planner would otherwise pick a sequential scan.
  perform set_config('enable_seqscan', 'off', true);
  pool := least(greatest(pool, 1), 50);
  q := array_to_string(
    regexp_split_to_array(trim(pgroonga_query_escape(coalesce(query_text, ''))), '\s+'), ' OR '
  );
  return query
  with vec as (
    select c.id, (row_number() over (order by c.embedding <=> query_embedding))::int as r
    from public.chunks c
    where product_filter is null or c.product = product_filter or c.product is null
    order by c.embedding <=> query_embedding
    limit pool
  ),
  kw as (
    select c.id, (row_number() over (order by pgroonga_score(c.tableoid, c.ctid) desc))::int as r
    from public.chunks c
    where q <> '' and c.content &@~ q
      and (product_filter is null or c.product = product_filter or c.product is null)
    order by pgroonga_score(c.tableoid, c.ctid) desc
    limit pool
  )
  select c.id, c.title, c.url, c.license, c.source_type, c.lang, c.product, c.safety_level,
         c.content, vec.r, kw.r
  from public.chunks c
  left join vec on vec.id = c.id
  left join kw on kw.id = c.id
  where vec.id is not null or kw.id is not null;
end;
$$;

create or replace function public.ingest_chunks(token text, rows jsonb)
returns int
language plpgsql
security definer
set search_path = public, extensions, private
as $$
declare
  n int;
begin
  if not exists (
    select 1 from private.ingest_tokens where token_hash = encode(extensions.digest(token, 'sha256'), 'hex')
  ) then
    raise exception 'invalid ingest token' using errcode = '28000';
  end if;
  insert into public.chunks (id, source_type, title, url, license, lang, product, safety_level, content, embedding, updated_at)
  select r->>'id', r->>'source_type', r->>'title', r->>'url', r->>'license', r->>'lang', r->>'product',
         (r->>'safety_level')::int, r->>'text', (r->>'embedding')::extensions.vector, now()
  from jsonb_array_elements(rows) r
  on conflict (id) do update set
    source_type = excluded.source_type, title = excluded.title, url = excluded.url,
    license = excluded.license, lang = excluded.lang, product = excluded.product,
    safety_level = excluded.safety_level, content = excluded.content,
    embedding = excluded.embedding, updated_at = now();
  get diagnostics n = row_count;
  return n;
end;
$$;

create or replace function public.prune_chunks(token text, keep_ids text[])
returns int
language plpgsql
security definer
set search_path = public, extensions, private
as $$
declare
  n int;
begin
  if not exists (
    select 1 from private.ingest_tokens where token_hash = encode(extensions.digest(token, 'sha256'), 'hex')
  ) then
    raise exception 'invalid ingest token' using errcode = '28000';
  end if;
  delete from public.chunks where id <> all (keep_ids);
  get diagnostics n = row_count;
  return n;
end;
$$;

revoke all on function public.search_chunks(text, extensions.vector, text, int) from public;
revoke all on function public.ingest_chunks(text, jsonb) from public;
revoke all on function public.prune_chunks(text, text[]) from public;
grant execute on function public.search_chunks(text, extensions.vector, text, int) to anon, authenticated;
grant execute on function public.ingest_chunks(text, jsonb) to anon;
grant execute on function public.prune_chunks(text, text[]) to anon;
