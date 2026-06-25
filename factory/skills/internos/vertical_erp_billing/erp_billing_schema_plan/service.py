from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import schema_identifier  # noqa: E402


class ErpBillingSchemaPlanService:
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
                "tables": [
                    "billing_money_accounts",
                    "billing_collection_folios",
                    "billing_payments",
                    "billing_payment_applications",
                    "billing_anticipos",
                    "billing_devoluciones",
                    "billing_cash_cuts",
                    "billing_events",
                ],
            },
        }

    def _sql(self, schema: str) -> str:
        return f"""create schema if not exists {schema};

create table if not exists {schema}.erp_folio_sequences (
  id uuid primary key default gen_random_uuid(),
  folio text unique not null,
  empresa_id text not null,
  project_code text not null,
  module_code text not null,
  scope text not null,
  prefix text not null,
  current_number integer not null default 0,
  digits integer not null default 5,
  erp_tags jsonb not null default '{{}}',
  metadata jsonb not null default '{{}}',
  created_at timestamptz not null default now(),
  updated_at timestamptz,
  constraint erp_folio_sequences_digits_check check (digits between 1 and 12),
  constraint erp_folio_sequences_current_check check (current_number >= 0),
  constraint erp_folio_sequences_scope_unique unique (empresa_id, project_code, module_code, scope, prefix)
);

create or replace function {schema}.reserve_erp_folio(
  p_scope text,
  p_prefix text,
  p_digits integer default 5,
  p_empresa_id text default '',
  p_project_code text default '',
  p_module_code text default '',
  p_min_current integer default 0
)
returns text
language plpgsql
security definer
set search_path = {schema}, public
as $$
declare
  v_number integer;
  v_prefix text;
  v_scope text;
begin
  v_prefix := upper(trim(p_prefix));
  v_scope := lower(trim(p_scope));

  if v_prefix !~ '^[A-Z0-9_]{{2,12}}$' then
    raise exception 'prefix invalido: %', p_prefix;
  end if;
  if v_scope !~ '^[a-z0-9_]{{2,80}}$' then
    raise exception 'scope invalido: %', p_scope;
  end if;
  if p_digits is null or p_digits < 1 or p_digits > 12 then
    raise exception 'digits invalido: %', p_digits;
  end if;
  if p_empresa_id is null or trim(p_empresa_id) = '' then
    raise exception 'empresa_id requerido';
  end if;
  if p_project_code is null or trim(p_project_code) = '' then
    raise exception 'project_code requerido';
  end if;
  if p_module_code is null or trim(p_module_code) = '' then
    raise exception 'module_code requerido';
  end if;
  if p_min_current is null or p_min_current < 0 then
    p_min_current := 0;
  end if;

  insert into {schema}.erp_folio_sequences (
    folio,
    empresa_id,
    project_code,
    module_code,
    scope,
    prefix,
    current_number,
    digits
  )
  values (
    'SEQ-' || upper(regexp_replace(coalesce(p_module_code, 'erp'), '[^A-Za-z0-9]+', '_', 'g')) || '-' || v_scope || '-' || v_prefix,
    p_empresa_id,
    p_project_code,
    p_module_code,
    v_scope,
    v_prefix,
    p_min_current,
    p_digits
  )
  on conflict (empresa_id, project_code, module_code, scope, prefix) do nothing;

  update {schema}.erp_folio_sequences
  set current_number = greatest(current_number, p_min_current) + 1,
      digits = p_digits,
      updated_at = now()
  where empresa_id = p_empresa_id
    and project_code = p_project_code
    and module_code = p_module_code
    and scope = v_scope
    and prefix = v_prefix
  returning current_number into v_number;

  return v_prefix || '-' || lpad(v_number::text, p_digits, '0');
end;
$$;

create table if not exists {schema}.billing_money_accounts (
  id uuid primary key default gen_random_uuid(),
  folio text unique not null,
  empresa_id text not null,
  project_code text not null,
  module_code text not null,
  account_type text not null check (account_type in ('bank','cash','cash_box','collector_cash','card_terminal','other')),
  account_name text not null,
  bank_name text,
  account_number_mask text,
  holder_name text,
  currency text not null default 'MXN',
  responsible_user text,
  status text not null default 'active',
  opening_balance numeric(14,2) not null default 0,
  current_balance numeric(14,2) not null default 0,
  metadata jsonb not null default '{{}}',
  created_at timestamptz not null default now(),
  updated_at timestamptz
);

create table if not exists {schema}.billing_collection_folios (
  id uuid primary key default gen_random_uuid(),
  folio text unique not null,
  empresa_id text not null,
  project_code text not null,
  module_code text not null,
  sales_schema text,
  sales_document_id uuid,
  sales_folio text,
  customer_id uuid,
  customer_name text,
  expected_amount numeric(14,2) not null default 0,
  collected_amount numeric(14,2) not null default 0,
  balance_amount numeric(14,2) not null default 0,
  status text not null default 'emitido',
  collector_name text,
  due_date date,
  uploaded_receipt_url text,
  uploaded_receipt_path text,
  ocr_status text not null default 'not_required',
  payment_id uuid,
  metadata jsonb not null default '{{}}',
  created_at timestamptz not null default now(),
  updated_at timestamptz
);

create table if not exists {schema}.billing_payments (
  id uuid primary key default gen_random_uuid(),
  folio text unique not null,
  empresa_id text not null,
  project_code text not null,
  module_code text not null,
  collection_folio_id uuid references {schema}.billing_collection_folios(id),
  collection_folio text,
  customer_id uuid,
  customer_name text,
  payment_method text not null check (payment_method in ('cash','transfer','deposit','card','check','other')),
  amount numeric(14,2) not null,
  unapplied_amount numeric(14,2) not null default 0,
  payment_date date not null default current_date,
  source_money_account_id uuid references {schema}.billing_money_accounts(id),
  destination_money_account_id uuid references {schema}.billing_money_accounts(id),
  bank_name text,
  sender_account text,
  receiver_account text,
  tracking_key text,
  reference text,
  receipt_file_url text,
  receipt_file_path text,
  receipt_file_bucket text,
  ocr_status text not null default 'not_required',
  validation_status text not null default 'manual',
  status text not null default 'capturado',
  notes text,
  metadata jsonb not null default '{{}}',
  created_at timestamptz not null default now(),
  updated_at timestamptz
);

create table if not exists {schema}.billing_payment_applications (
  id uuid primary key default gen_random_uuid(),
  folio text unique not null,
  empresa_id text not null,
  project_code text not null,
  module_code text not null,
  payment_id uuid not null references {schema}.billing_payments(id),
  payment_folio text not null,
  sales_schema text not null,
  sales_document_id uuid not null,
  sales_folio text,
  amount_applied numeric(14,2) not null,
  status text not null default 'aplicado',
  metadata jsonb not null default '{{}}',
  created_at timestamptz not null default now(),
  updated_at timestamptz
);

alter table if exists {schema}.billing_payments
  add column if not exists confirmation_status text not null default 'confirmado',
  add column if not exists bank_reference text,
  add column if not exists confirmed_at timestamptz,
  add column if not exists cash_cut_id uuid;

create table if not exists {schema}.billing_anticipos (
  id uuid primary key default gen_random_uuid(),
  folio text unique not null,
  empresa_id text not null,
  project_code text not null,
  module_code text not null,
  customer_id uuid,
  customer_name text,
  amount numeric(14,2) not null,
  unapplied_amount numeric(14,2) not null default 0,
  payment_method text not null check (payment_method in ('cash','transfer','deposit','card','check','other')),
  payment_date date not null default current_date,
  destination_money_account_id uuid references {schema}.billing_money_accounts(id),
  bank_name text,
  reference text,
  tracking_key text,
  receipt_file_url text,
  notes text,
  status text not null default 'disponible',
  metadata jsonb not null default '{{}}',
  created_at timestamptz not null default now(),
  updated_at timestamptz
);

create table if not exists {schema}.billing_devoluciones (
  id uuid primary key default gen_random_uuid(),
  folio text unique not null,
  empresa_id text not null,
  project_code text not null,
  module_code text not null,
  customer_id uuid,
  customer_name text,
  sales_schema text,
  sales_document_id uuid,
  sales_folio text,
  amount numeric(14,2) not null,
  reason text,
  status text not null default 'pendiente',
  resolution text,
  anticipo_id uuid,
  notes text,
  metadata jsonb not null default '{{}}',
  created_at timestamptz not null default now(),
  updated_at timestamptz
);

create index if not exists idx_billing_anticipos_customer on {schema}.billing_anticipos (empresa_id, customer_id, status);
create index if not exists idx_billing_devoluciones_customer on {schema}.billing_devoluciones (empresa_id, customer_id, status);

create table if not exists {schema}.billing_cash_cuts (
  id uuid primary key default gen_random_uuid(),
  folio text unique not null,
  empresa_id text not null,
  project_code text not null,
  module_code text not null,
  collector_name text,
  money_account_id uuid references {schema}.billing_money_accounts(id),
  cut_date date not null default current_date,
  expected_amount numeric(14,2) not null default 0,
  counted_amount numeric(14,2) not null default 0,
  difference_amount numeric(14,2) not null default 0,
  status text not null default 'abierto',
  notes text,
  metadata jsonb not null default '{{}}',
  created_at timestamptz not null default now(),
  updated_at timestamptz
);

create table if not exists {schema}.billing_events (
  id uuid primary key default gen_random_uuid(),
  folio text unique not null,
  empresa_id text not null,
  project_code text not null,
  module_code text not null,
  event_type text not null,
  payload jsonb not null default '{{}}',
  created_at timestamptz not null default now(),
  updated_at timestamptz
);

create index if not exists idx_billing_payments_customer on {schema}.billing_payments (empresa_id, customer_id, payment_date);
create index if not exists idx_billing_payments_status on {schema}.billing_payments (empresa_id, status, payment_date);
create index if not exists idx_billing_collection_status on {schema}.billing_collection_folios (empresa_id, status, created_at);
create index if not exists idx_billing_applications_doc on {schema}.billing_payment_applications (sales_schema, sales_document_id);
create index if not exists idx_erp_folio_sequences_scope on {schema}.erp_folio_sequences (empresa_id, project_code, module_code, scope, prefix);
notify pgrst, 'reload schema';"""
