create schema if not exists freelance;

create table if not exists freelance.jobs (
  id uuid primary key default gen_random_uuid(),
  company_id text not null default 'EMP_FREELANCE_GROWTH',
  source text not null default 'upwork',
  job_text text not null,
  score integer,
  decision text,
  decision_es text,
  matched_terms jsonb not null default '[]'::jsonb,
  risk_terms jsonb not null default '[]'::jsonb,
  relevant_projects jsonb not null default '[]'::jsonb,
  strengths jsonb not null default '[]'::jsonb,
  risks jsonb not null default '[]'::jsonb,
  proposal_angle text,
  saved_file text,
  status text not null default 'analyzed',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists freelance.proposals (
  id uuid primary key default gen_random_uuid(),
  company_id text not null default 'EMP_FREELANCE_GROWTH',
  source text not null default 'upwork',
  job_id uuid references freelance.jobs(id) on delete set null,
  job_text text,
  proposal_text text not null,
  matched_projects jsonb not null default '[]'::jsonb,
  saved_file text,
  status text not null default 'draft',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists freelance.tasks (
  id uuid primary key default gen_random_uuid(),
  company_id text not null default 'EMP_FREELANCE_GROWTH',
  area text not null default 'upwork_registration',
  title text not null,
  done boolean not null default false,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists freelance.assets (
  id uuid primary key default gen_random_uuid(),
  company_id text not null default 'EMP_FREELANCE_GROWTH',
  project_id text not null,
  asset_type text not null,
  title text,
  url text,
  notes text,
  created_at timestamptz not null default now()
);

create index if not exists freelance_jobs_created_idx on freelance.jobs (created_at desc);
create index if not exists freelance_jobs_score_idx on freelance.jobs (score desc);
create index if not exists freelance_proposals_created_idx on freelance.proposals (created_at desc);
create index if not exists freelance_tasks_area_idx on freelance.tasks (area, done);
create index if not exists freelance_assets_project_idx on freelance.assets (project_id);

grant usage on schema freelance to anon, authenticated, service_role;
grant all on all tables in schema freelance to anon, authenticated, service_role;
grant all on all sequences in schema freelance to anon, authenticated, service_role;
alter default privileges in schema freelance grant all on tables to anon, authenticated, service_role;
alter default privileges in schema freelance grant all on sequences to anon, authenticated, service_role;

alter role authenticator set pgrst.db_schemas = 'public,storage,graphql_public,estoikolab,logplat,freelance';
notify pgrst, 'reload config';
notify pgrst, 'reload schema';
