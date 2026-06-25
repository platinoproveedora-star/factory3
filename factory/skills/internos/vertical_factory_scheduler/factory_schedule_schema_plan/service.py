from __future__ import annotations


class FactoryScheduleSchemaPlanService:
    def ejecutar(self, context: dict) -> dict:
        schema = str(context.get("schema") or "public").strip()
        if not schema.replace("_", "").isalnum():
            return {"ok": False, "error": "schema invalido"}
        return {"ok": True, "data": {"schema": schema, "sql": self._sql(schema)}}

    def _sql(self, schema: str) -> str:
        return f"""create schema if not exists {schema};

create table if not exists {schema}.factory_schedules (
  id uuid primary key default gen_random_uuid(),
  folio text unique not null,
  schedule_name text unique not null,
  empresa_id text,
  project_code text,
  module_code text,
  skill_name text not null,
  skill_source text not null default 'internos',
  context jsonb not null default '{{}}',
  timezone text not null default 'America/Mexico_City',
  schedule_type text not null default 'daily' check (schedule_type in ('daily','hourly','interval_minutes','once')),
  local_time text,
  interval_minutes integer,
  status text not null default 'active' check (status in ('active','paused','disabled')),
  next_run_at timestamptz,
  last_run_at timestamptz,
  last_status text,
  last_error text,
  last_result jsonb,
  metadata jsonb not null default '{{}}',
  created_at timestamptz not null default now(),
  updated_at timestamptz
);

create table if not exists {schema}.factory_schedule_runs (
  id uuid primary key default gen_random_uuid(),
  folio text unique not null,
  schedule_id uuid references {schema}.factory_schedules(id),
  schedule_folio text,
  schedule_name text,
  empresa_id text,
  project_code text,
  module_code text,
  skill_name text not null,
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  status text not null default 'running',
  result jsonb,
  error text,
  metadata jsonb not null default '{{}}'
);

create index if not exists idx_factory_schedules_due on {schema}.factory_schedules (status, next_run_at);
create index if not exists idx_factory_schedule_runs_schedule on {schema}.factory_schedule_runs (schedule_id, started_at desc);
notify pgrst, 'reload schema';"""
