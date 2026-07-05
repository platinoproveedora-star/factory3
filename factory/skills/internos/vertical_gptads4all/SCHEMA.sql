-- GPTAds4All schema v1.0 - multi-tenant por empresa_id
-- DOCUMENTACION: no ejecutar sin aprobacion humana.

create schema if not exists gptads4all;

create table if not exists gptads4all.products (
  id uuid primary key default gen_random_uuid(),
  folio text unique not null default ('gptads_' || replace(gen_random_uuid()::text, '-', '')),
  empresa_id text not null,
  product_key text not null,
  product_name text not null,
  description text,
  category text,
  price_range text,
  url text,
  market jsonb,
  value_props jsonb,
  tone text,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  unique (empresa_id, product_key)
);

create table if not exists gptads4all.intents (
  id uuid primary key default gen_random_uuid(),
  folio text unique not null default ('gptads_' || replace(gen_random_uuid()::text, '-', '')),
  empresa_id text not null,
  product_key text not null,
  intent_id text not null,
  intent_text text not null,
  intent_type text,
  funnel_stage text,
  priority int default 1,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  unique (empresa_id, product_key, intent_id)
);

create table if not exists gptads4all.context_hints (
  id uuid primary key default gen_random_uuid(),
  folio text unique not null default ('gptads_' || replace(gen_random_uuid()::text, '-', '')),
  empresa_id text not null,
  product_key text not null,
  hint_id text not null,
  intent_id text not null,
  hint_text text not null,
  trigger_keywords jsonb,
  priority int default 1,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  unique (empresa_id, product_key, hint_id)
);

create table if not exists gptads4all.campaigns (
  id uuid primary key default gen_random_uuid(),
  folio text unique not null default ('gptads_' || replace(gen_random_uuid()::text, '-', '')),
  empresa_id text not null,
  product_key text not null,
  campaign_key text not null,
  campaign_name text not null,
  objective text,
  daily_budget_amount numeric,
  currency text default 'MXN',
  status text default 'draft',
  intent_ids jsonb,
  hint_ids jsonb,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  unique (empresa_id, campaign_key)
);

create table if not exists gptads4all.creatives (
  id uuid primary key default gen_random_uuid(),
  folio text unique not null default ('gptads_' || replace(gen_random_uuid()::text, '-', '')),
  empresa_id text not null,
  campaign_key text not null,
  creative_id text not null,
  intent_id text,
  headline text not null,
  body text,
  cta text,
  variant int default 1,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  unique (empresa_id, campaign_key, creative_id)
);

create table if not exists gptads4all.exports (
  id uuid primary key default gen_random_uuid(),
  folio text unique not null default ('gptads_' || replace(gen_random_uuid()::text, '-', '')),
  empresa_id text not null,
  campaign_key text not null,
  format text not null,
  file_path text,
  rows_exported int,
  generated_at timestamptz default now(),
  updated_at timestamptz default now()
);

alter table if exists gptads4all.products add column if not exists folio text unique not null default ('gptads_' || replace(gen_random_uuid()::text, '-', ''));
alter table if exists gptads4all.intents add column if not exists folio text unique not null default ('gptads_' || replace(gen_random_uuid()::text, '-', ''));
alter table if exists gptads4all.context_hints add column if not exists folio text unique not null default ('gptads_' || replace(gen_random_uuid()::text, '-', ''));
alter table if exists gptads4all.context_hints add column if not exists trigger_keywords jsonb;
alter table if exists gptads4all.campaigns add column if not exists folio text unique not null default ('gptads_' || replace(gen_random_uuid()::text, '-', ''));
alter table if exists gptads4all.creatives add column if not exists folio text unique not null default ('gptads_' || replace(gen_random_uuid()::text, '-', ''));
alter table if exists gptads4all.exports add column if not exists folio text unique not null default ('gptads_' || replace(gen_random_uuid()::text, '-', ''));
