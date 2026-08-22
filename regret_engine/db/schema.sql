create extension if not exists vector;

create table if not exists guardian_decisions (
    id uuid primary key default gen_random_uuid(),
    decision_id text not null unique,
    occurred_at timestamptz not null,
    sku text not null,
    price numeric not null,
    risk_level text not null check (risk_level in ('LOW', 'MEDIUM', 'HIGH')),
    regret_score numeric not null,
    confidence numeric not null,
    input_json jsonb not null,
    record_json jsonb not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists guardian_decisions_occurred_at_idx
    on guardian_decisions (occurred_at desc);

create index if not exists guardian_decisions_risk_level_idx
    on guardian_decisions (risk_level);

create table if not exists guardian_knowledge_chunks (
    id uuid primary key default gen_random_uuid(),
    source text not null unique,
    title text not null,
    content text not null,
    embedding vector(768) not null,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists guardian_knowledge_chunks_embedding_idx
    on guardian_knowledge_chunks
    using hnsw (embedding vector_cosine_ops);

create or replace function match_guardian_knowledge_chunks(
    query_embedding vector(768),
    match_threshold double precision default 0.2,
    match_count integer default 5
)
returns table (
    source text,
    title text,
    content text,
    relevance_score double precision
)
language sql
stable
security invoker
as $$
    select
        guardian_knowledge_chunks.source,
        guardian_knowledge_chunks.title,
        guardian_knowledge_chunks.content,
        1 - (guardian_knowledge_chunks.embedding <=> query_embedding) as relevance_score
    from guardian_knowledge_chunks
    where 1 - (guardian_knowledge_chunks.embedding <=> query_embedding) >= match_threshold
    order by guardian_knowledge_chunks.embedding <=> query_embedding
    limit match_count;
$$;

alter table guardian_decisions enable row level security;
alter table guardian_knowledge_chunks enable row level security;
