from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import schema_identifier  # noqa: E402


class ErpBanksSchemaPlanService:
    def ejecutar(self, context: dict) -> dict:
        try:
            schema = schema_identifier(context)
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}
        sql = self._sql(schema)
        return {
            "ok": True,
            "data": {
                "schema": schema,
                "sql": sql,
                "tables": ["banks_accounts", "banks_movements", "erp_folio_sequences"],
            },
        }

    def _sql(self, s: str) -> str:
        return f"""-- ERP Banks schema: {s}
-- Ejecutar en Supabase SQL Editor
-- Exponer schema en: Dashboard > Settings > Data API > Exposed schemas

create schema if not exists {s};

create table if not exists {s}.erp_folio_sequences (
  id uuid primary key default gen_random_uuid(),
  folio text unique not null,
  empresa_id text not null,
  project_code text not null,
  module_code text not null,
  scope text not null,
  prefix text not null,
  current_number integer not null default 0,
  digits integer not null default 5,
  metadata jsonb not null default '{{}}',
  created_at timestamptz not null default now(),
  updated_at timestamptz,
  constraint erp_folio_sequences_scope_unique unique (empresa_id, project_code, module_code, scope, prefix)
);

create or replace function {s}.reserve_erp_folio(
  p_scope text, p_prefix text, p_digits integer default 5,
  p_empresa_id text default '', p_project_code text default '', p_module_code text default '',
  p_min_current integer default 0
) returns text language plpgsql security definer set search_path = {s}, public as $$
declare v_number integer; v_prefix text; v_scope text;
begin
  v_prefix := upper(trim(p_prefix));
  v_scope  := lower(trim(p_scope));
  insert into {s}.erp_folio_sequences (folio, empresa_id, project_code, module_code, scope, prefix, current_number, digits)
    values (v_scope || '_seq', p_empresa_id, p_project_code, p_module_code, v_scope, v_prefix, p_min_current, p_digits)
    on conflict (empresa_id, project_code, module_code, scope, prefix) do nothing;
  update {s}.erp_folio_sequences
    set current_number = current_number + 1, updated_at = now()
    where empresa_id = p_empresa_id and project_code = p_project_code
      and module_code = p_module_code and scope = v_scope and prefix = v_prefix
    returning current_number into v_number;
  return v_prefix || '-' || lpad(v_number::text, p_digits, '0');
end;
$$;

create table if not exists {s}.banks_accounts (
  id uuid primary key default gen_random_uuid(),
  folio text unique not null,
  empresa_id text not null,
  project_code text not null,
  module_code text not null default 'banks',
  account_type text not null,
  account_name text not null,
  bank_name text,
  account_number text,
  account_number_mask text,
  holder_name text,
  currency text not null default 'MXN',
  responsible_user text,
  status text not null default 'active',
  current_balance numeric(14,2) not null default 0,
  opening_balance numeric(14,2) not null default 0,
  metadata jsonb not null default '{{}}',
  created_at timestamptz not null default now(),
  updated_at timestamptz
);

create table if not exists {s}.banks_movements (
  id uuid primary key default gen_random_uuid(),
  folio text unique not null,
  empresa_id text not null,
  project_code text not null,
  module_code text not null default 'banks',
  account_id uuid not null references {s}.banks_accounts(id),
  account_folio text not null,
  movement_type text not null,
  source_type text not null,
  source_id text,
  source_folio text,
  amount numeric(14,2) not null,
  balance_after numeric(14,2) not null,
  movement_date date not null,
  notes text,
  metadata jsonb not null default '{{}}',
  created_at timestamptz not null default now()
);

-- Indexes
create index if not exists banks_accounts_empresa_idx on {s}.banks_accounts(empresa_id);
create index if not exists banks_accounts_status_idx on {s}.banks_accounts(status);
create index if not exists banks_movements_account_idx on {s}.banks_movements(account_id);
create index if not exists banks_movements_source_idx on {s}.banks_movements(source_type, source_id);
create index if not exists banks_movements_date_idx on {s}.banks_movements(movement_date desc);
"""
