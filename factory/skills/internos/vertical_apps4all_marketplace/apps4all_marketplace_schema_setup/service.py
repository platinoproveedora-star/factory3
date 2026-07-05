from __future__ import annotations

from factory.engine import SupabaseClient


SQL = """
create schema if not exists platform;

create table if not exists platform.modulos (
  code text primary key,
  nombre text not null,
  activo boolean not null default true,
  app_url text null,
  icon text null,
  sort_order integer not null default 100,
  stripe_product_id text null,
  default_plan_code text null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

alter table platform.modulos
  add column if not exists description text null,
  add column if not exists category text null,
  add column if not exists marketplace_status text not null default 'draft',
  add column if not exists demo_url text null,
  add column if not exists prod_url text null,
  add column if not exists pricing_json jsonb not null default '{}'::jsonb,
  add column if not exists tags jsonb not null default '[]'::jsonb,
  add column if not exists updated_at timestamptz null;

create table if not exists platform.marketplace_events (
  id uuid primary key default gen_random_uuid(),
  folio text unique not null default ('mkt_' || replace(gen_random_uuid()::text, '-', '')),
  module_code text not null,
  company_id text null,
  user_id uuid null,
  event_type text not null,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

grant usage on schema platform to anon, authenticated, service_role;
grant select on platform.modulos to anon, authenticated;
grant all on platform.modulos to service_role;
grant all on platform.marketplace_events to service_role;
notify pgrst, 'reload schema';
"""


class Apps4AllMarketplaceSchemaSetupService:
    def ejecutar(self, context: dict) -> dict:
        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run", "data": {"sql": SQL}}
        result = SupabaseClient({"schema": "platform"}).management_query(SQL)
        if not result.get("ok"):
            return result
        return {"ok": True, "message": "marketplace schema ready", "data": {"schema": "platform"}}
