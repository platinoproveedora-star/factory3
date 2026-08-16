from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


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

create table if not exists platform.tenant_sources (
  id uuid primary key default gen_random_uuid(),
  company_id text not null,
  module_code text not null,
  source_key text not null,
  source_schema text not null,
  source_project_code text,
  enabled boolean not null default true,
  config jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (company_id, module_code, source_key)
);

grant usage on schema platform to anon, authenticated, service_role;
grant select on platform.modulos to anon, authenticated;
grant all on platform.modulos to service_role;
grant all on platform.marketplace_events to service_role;
grant all on platform.tenant_sources to service_role;
notify pgrst, 'reload schema';
"""


class Apps4AllMarketplaceSchemaSetupService:
    """platform.* vive en el proyecto Supabase de la plataforma (PLATFORM_SUPABASE_*),
    que es distinto del proyecto Supabase operativo de cada empresa (SUPABASE_*).
    No usar SupabaseClient generico aqui: siempre apunta a SUPABASE_URL/ACCESS_TOKEN.
    """

    def ejecutar(self, context: dict) -> dict:
        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run", "data": {"sql": SQL}}

        access_token = (context.get("platform_supabase_access_token") or os.getenv("PLATFORM_SUPABASE_ACCESS_TOKEN", "")).strip()
        project_ref = (context.get("platform_supabase_project_ref") or os.getenv("PLATFORM_SUPABASE_PROJECT_REF", "")).strip()
        if not access_token or not project_ref:
            return {"ok": False, "error": "Faltan PLATFORM_SUPABASE_ACCESS_TOKEN o PLATFORM_SUPABASE_PROJECT_REF"}

        endpoint = f"https://api.supabase.com/v1/projects/{project_ref}/database/query"
        req = urllib.request.Request(
            endpoint,
            data=json.dumps({"query": SQL}).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "User-Agent": "FactoryFactory/0.1 (+https://github.com/)",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                resp.read()
        except urllib.error.HTTPError as exc:
            return {"ok": False, "error": f"HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')}"}
        return {"ok": True, "message": "marketplace schema ready", "data": {"schema": "platform"}}
