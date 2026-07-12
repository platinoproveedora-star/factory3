from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import schema_identifier  # noqa: E402


class ErpClientFollowupSchemaPlanService:
    def ejecutar(self, context: dict) -> dict:
        try:
            schema = schema_identifier(context)
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}
        return {
            "ok": True,
            "data": {
                "schema": schema,
                "tables": ["erp_client_followups"],
                "sql": self._sql(schema),
            },
        }

    def _sql(self, schema: str) -> str:
        return f"""create schema if not exists {schema};

create table if not exists {schema}.erp_client_followups (
  id uuid primary key default gen_random_uuid(),
  folio text unique not null,
  empresa_id text not null,
  project_code text not null,
  module_code text not null,
  customer_id uuid,
  customer_key text not null,
  customer_name text not null,
  comments text,
  last_call_date date,
  next_followup_date date,
  offer_prices text,
  status text not null default 'activo',
  metadata jsonb not null default '{{}}',
  created_at timestamptz not null default now(),
  updated_at timestamptz,
  constraint erp_client_followups_customer_unique unique (empresa_id, project_code, module_code, customer_key)
);

alter table if exists {schema}.erp_client_followups
  add column if not exists phone text;

create index if not exists erp_client_followups_next_followup_idx
  on {schema}.erp_client_followups (empresa_id, project_code, module_code, next_followup_date);

create index if not exists erp_client_followups_customer_key_idx
  on {schema}.erp_client_followups (customer_key);

notify pgrst, 'reload schema';
"""
