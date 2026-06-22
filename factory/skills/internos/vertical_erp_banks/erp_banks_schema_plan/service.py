from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _banks_common import resolve_banks_context, schema_identifier  # noqa: E402


class ErpBanksSchemaPlanService:
    def ejecutar(self, context: dict) -> dict:
        try:
            schema = schema_identifier(context)
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}

        ctx_result = resolve_banks_context({**context, "schema": schema})
        if not ctx_result.get("ok"):
            return ctx_result
        ctx = ctx_result["data"]

        sql = self._sql(schema, ctx["company_id"], ctx["project_code"], ctx["module_code"])
        return {
            "ok": True,
            "data": {
                "schema": schema,
                "company_id": ctx["company_id"],
                "project_code": ctx["project_code"],
                "module_code": ctx["module_code"],
                "sql": sql,
                "tables": ["banks_accounts", "banks_movements", "banks_authorization_rules", "banks_authorizations", "erp_folio_sequences"],
            },
        }

    def _sql(self, s: str, company_id: str, project_code: str, module_code: str) -> str:
        company_sql = company_id.replace("'", "''")
        project_sql = project_code.replace("'", "''")
        module_sql = module_code.replace("'", "''")
        return f"""-- ERP Banks schema: {s}
-- Empresa: {company_sql}
-- Proyecto: {project_sql}
-- Ejecutar en Supabase SQL Editor o via vertical_supabase/supabase_sql_execute.
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
  source_module text,
  source_id text,
  source_folio text,
  amount numeric(14,2) not null,
  balance_before numeric(14,2),
  balance_after numeric(14,2),
  movement_date date not null,
  transfer_group_id uuid,
  reversal_of_movement_id uuid references {s}.banks_movements(id),
  authorization_status text not null default 'no_requerida',
  authorization_id uuid,
  clave_rastreo text,
  value_date date,
  reconciliation_status text not null default 'pendiente',
  reconciled_at timestamptz,
  notes text,
  metadata jsonb not null default '{{}}',
  created_at timestamptz not null default now(),
  updated_at timestamptz
);

alter table {s}.banks_movements
  add column if not exists source_module text,
  add column if not exists balance_before numeric(14,2),
  add column if not exists transfer_group_id uuid,
  add column if not exists reversal_of_movement_id uuid references {s}.banks_movements(id),
  add column if not exists authorization_status text not null default 'no_requerida',
  add column if not exists authorization_id uuid,
  add column if not exists clave_rastreo text,
  add column if not exists value_date date,
  add column if not exists reconciliation_status text not null default 'pendiente',
  add column if not exists reconciled_at timestamptz,
  add column if not exists updated_at timestamptz;

alter table {s}.banks_movements alter column balance_after drop not null;

do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'banks_movements_movement_type_chk' and conrelid = '{s}.banks_movements'::regclass) then
    alter table {s}.banks_movements add constraint banks_movements_movement_type_chk check (movement_type in ('entrada','salida')) not valid;
    alter table {s}.banks_movements validate constraint banks_movements_movement_type_chk;
  end if;
  if not exists (select 1 from pg_constraint where conname = 'banks_movements_source_type_chk' and conrelid = '{s}.banks_movements'::regclass) then
    alter table {s}.banks_movements add constraint banks_movements_source_type_chk check (source_type in ('pago','transferencia','ajuste','corte','apertura','devolucion')) not valid;
    alter table {s}.banks_movements validate constraint banks_movements_source_type_chk;
  end if;
  if not exists (select 1 from pg_constraint where conname = 'banks_movements_authorization_status_chk' and conrelid = '{s}.banks_movements'::regclass) then
    alter table {s}.banks_movements add constraint banks_movements_authorization_status_chk check (authorization_status in ('no_requerida','pendiente','autorizado','rechazado')) not valid;
    alter table {s}.banks_movements validate constraint banks_movements_authorization_status_chk;
  end if;
  alter table {s}.banks_movements drop constraint if exists banks_movements_reconciliation_status_chk;
  alter table {s}.banks_movements add constraint banks_movements_reconciliation_status_chk check (reconciliation_status in ('pendiente','revisado','conciliado','revisado_conciliado')) not valid;
  if not exists (select 1 from pg_constraint where conname = 'banks_movements_transfer_group_chk' and conrelid = '{s}.banks_movements'::regclass) then
    alter table {s}.banks_movements add constraint banks_movements_transfer_group_chk check (source_type <> 'transferencia' or transfer_group_id is not null) not valid;
    alter table {s}.banks_movements validate constraint banks_movements_transfer_group_chk;
  end if;
end $$;

create table if not exists {s}.banks_authorization_rules (
  id uuid primary key default gen_random_uuid(),
  folio text unique not null,
  empresa_id text not null,
  project_code text not null,
  module_code text not null default 'banks',
  rule_name text not null,
  active boolean not null default true,
  applies_to_account_id uuid references {s}.banks_accounts(id),
  movement_type_filter text,
  source_type_filter text,
  source_module_filter text,
  min_amount numeric(14,2) not null constraint banks_authorization_rules_min_amount_chk check (min_amount >= 0),
  authorizer_user_id uuid,
  authorizer_role text,
  priority integer not null default 100,
  metadata jsonb not null default '{{}}',
  created_at timestamptz not null default now(),
  updated_at timestamptz
);

create table if not exists {s}.banks_authorizations (
  id uuid primary key default gen_random_uuid(),
  folio text unique not null,
  empresa_id text not null,
  project_code text not null,
  module_code text not null default 'banks',
  movement_id uuid not null references {s}.banks_movements(id),
  rule_id uuid references {s}.banks_authorization_rules(id),
  requested_by uuid,
  requested_at timestamptz not null default now(),
  status text not null default 'pendiente' constraint banks_authorizations_status_chk check (status in ('pendiente','aprobado','rechazado')),
  decided_by uuid,
  decided_at timestamptz,
  decision_notes text,
  metadata jsonb not null default '{{}}',
  created_at timestamptz not null default now(),
  updated_at timestamptz
);

create index if not exists banks_accounts_empresa_idx on {s}.banks_accounts(empresa_id);
create index if not exists banks_accounts_status_idx on {s}.banks_accounts(status);
create index if not exists banks_auth_rules_empresa_idx on {s}.banks_authorization_rules(empresa_id, active);
create index if not exists banks_auth_status_idx on {s}.banks_authorizations(empresa_id, status);
create index if not exists banks_movements_auth_idx on {s}.banks_movements(authorization_status);
create index if not exists banks_movements_reconcile_idx on {s}.banks_movements(account_id, reconciliation_status);
create index if not exists banks_movements_account_idx on {s}.banks_movements(account_id);
create index if not exists banks_movements_source_idx on {s}.banks_movements(source_type, source_id);
create index if not exists banks_movements_date_idx on {s}.banks_movements(movement_date desc);

create unique index if not exists banks_movements_source_unique_idx
on {s}.banks_movements(source_module, source_type, source_id, movement_type)
where source_id is not null and reversal_of_movement_id is null;

insert into {s}.banks_authorization_rules (
  folio, empresa_id, project_code, module_code, rule_name, active,
  applies_to_account_id, movement_type_filter, source_type_filter,
  source_module_filter, min_amount, authorizer_user_id, priority
)
select
  {s}.reserve_erp_folio('banks_authorization_rules', 'BAR', 5, '{company_sql}', '{project_sql}', '{module_sql}'),
  '{company_sql}', '{project_sql}', '{module_sql}',
  'Forzar autorizacion en ajustes de reconciliacion', true,
  null, null, null, 'reconciliation', 0, null, 1
where not exists (
  select 1 from {s}.banks_authorization_rules
  where empresa_id = '{company_sql}' and project_code = '{project_sql}'
    and module_code = '{module_sql}' and source_module_filter = 'reconciliation'
);

create or replace function {s}.banks_record_movement(
  p_account_id uuid default null,
  p_account_folio text default null,
  p_movement_type text default '',
  p_source_type text default '',
  p_source_module text default null,
  p_source_id text default null,
  p_source_folio text default null,
  p_amount numeric default 0,
  p_movement_date date default current_date,
  p_transfer_group_id uuid default null,
  p_reversal_of_movement_id uuid default null,
  p_clave_rastreo text default null,
  p_value_date date default null,
  p_notes text default null,
  p_metadata jsonb default '{{}}'::jsonb,
  p_empresa_id text default '',
  p_project_code text default '',
  p_module_code text default 'banks',
  p_requested_by uuid default null
) returns jsonb language plpgsql security definer set search_path = {s}, public as $$
declare
  v_account {s}.banks_accounts%rowtype;
  v_existing {s}.banks_movements%rowtype;
  v_rule {s}.banks_authorization_rules%rowtype;
  v_movement {s}.banks_movements%rowtype;
  v_authorization {s}.banks_authorizations%rowtype;
  v_folio text;
  v_auth_folio text;
  v_balance_before numeric(14,2);
  v_balance_after numeric(14,2);
  v_auth_status text;
  v_source_module text;
begin
  if p_movement_type not in ('entrada','salida') then
    raise exception 'movement_type invalido';
  end if;
  if p_source_type not in ('pago','transferencia','ajuste','corte','apertura','devolucion') then
    raise exception 'source_type invalido';
  end if;
  if p_amount is null or p_amount <= 0 then
    raise exception 'amount debe ser mayor a 0';
  end if;
  if p_source_type = 'transferencia' and p_transfer_group_id is null then
    raise exception 'transfer_group_id requerido para transferencias';
  end if;
  v_source_module := coalesce(nullif(trim(p_source_module), ''), 'manual');

  if p_source_id is not null then
    select * into v_existing
    from {s}.banks_movements
    where empresa_id = p_empresa_id
      and source_module = v_source_module
      and source_type = p_source_type
      and source_id = p_source_id
      and movement_type = p_movement_type
      and reversal_of_movement_id is null
    limit 1;
    if found then
      return jsonb_build_object('ok', true, 'data', jsonb_build_object('movement', to_jsonb(v_existing), 'idempotent', true));
    end if;
  end if;

  select * into v_account
  from {s}.banks_accounts
  where (p_account_id is not null and id = p_account_id)
     or (p_account_id is null and p_account_folio is not null and folio = p_account_folio)
  for update;

  if not found then
    raise exception 'cuenta no encontrada';
  end if;
  if v_account.empresa_id <> p_empresa_id then
    raise exception 'cuenta no pertenece a esta empresa';
  end if;
  if v_account.status = 'closed' then
    raise exception 'cuenta cerrada, no acepta movimientos';
  end if;

  select * into v_rule
  from {s}.banks_authorization_rules
  where empresa_id = p_empresa_id
    and active = true
    and (applies_to_account_id is null or applies_to_account_id = v_account.id)
    and (movement_type_filter is null or movement_type_filter = p_movement_type)
    and (source_type_filter is null or source_type_filter = p_source_type)
    and (source_module_filter is null or source_module_filter = v_source_module)
    and min_amount <= p_amount
  order by priority asc, created_at asc, id asc
  limit 1;

  v_folio := {s}.reserve_erp_folio('banks_movements', 'BAM', 5, p_empresa_id, p_project_code, p_module_code);

  if found then
    v_auth_status := 'pendiente';
    v_balance_before := null;
    v_balance_after := null;
  else
    v_auth_status := 'no_requerida';
    v_balance_before := v_account.current_balance;
    v_balance_after := case when p_movement_type = 'entrada' then v_account.current_balance + p_amount else v_account.current_balance - p_amount end;
  end if;

  begin
    insert into {s}.banks_movements (
      folio, empresa_id, project_code, module_code, account_id, account_folio,
      movement_type, source_type, source_module, source_id, source_folio,
      amount, balance_before, balance_after, movement_date, transfer_group_id,
      reversal_of_movement_id, authorization_status, clave_rastreo, value_date,
      reconciliation_status, notes, metadata
    ) values (
      v_folio, p_empresa_id, p_project_code, p_module_code, v_account.id, v_account.folio,
      p_movement_type, p_source_type, v_source_module, p_source_id, p_source_folio,
      p_amount, v_balance_before, v_balance_after, coalesce(p_movement_date, current_date), p_transfer_group_id,
      p_reversal_of_movement_id, v_auth_status, p_clave_rastreo, p_value_date,
      case when v_auth_status = 'pendiente' then 'pendiente' else 'pendiente' end,
      p_notes, coalesce(p_metadata, '{{}}'::jsonb)
    )
    returning * into v_movement;
  exception when unique_violation then
    if p_source_id is not null then
      select * into v_existing
      from {s}.banks_movements
      where empresa_id = p_empresa_id
        and source_module = v_source_module
        and source_type = p_source_type
        and source_id = p_source_id
        and movement_type = p_movement_type
        and reversal_of_movement_id is null
      limit 1;
      if found then
        return jsonb_build_object('ok', true, 'data', jsonb_build_object('movement', to_jsonb(v_existing), 'idempotent', true));
      end if;
    end if;
    raise;
  end;

  if v_auth_status = 'pendiente' then
    v_auth_folio := {s}.reserve_erp_folio('banks_authorizations', 'BAU', 5, p_empresa_id, p_project_code, p_module_code);
    insert into {s}.banks_authorizations (
      folio, empresa_id, project_code, module_code, movement_id, rule_id, requested_by, status
    ) values (
      v_auth_folio, p_empresa_id, p_project_code, p_module_code, v_movement.id, v_rule.id, p_requested_by, 'pendiente'
    )
    returning * into v_authorization;

    update {s}.banks_movements
    set authorization_id = v_authorization.id, updated_at = now()
    where id = v_movement.id
    returning * into v_movement;
  else
    update {s}.banks_accounts
    set current_balance = v_balance_after, updated_at = now()
    where id = v_account.id;
  end if;

  return jsonb_build_object(
    'ok', true,
    'data', jsonb_build_object(
      'movement', to_jsonb(v_movement),
      'authorization', case when v_authorization.id is null then null else to_jsonb(v_authorization) end,
      'balance_before', v_balance_before,
      'balance_after', v_balance_after,
      'idempotent', false
    )
  );
end;
$$;

create or replace function {s}.banks_decide_authorization(
  p_movement_id uuid,
  p_decision text,
  p_decided_by uuid,
  p_decision_notes text default null,
  p_empresa_id text default '',
  p_default_authorizer uuid default null
) returns jsonb language plpgsql security definer set search_path = {s}, public as $$
declare
  v_movement {s}.banks_movements%rowtype;
  v_account {s}.banks_accounts%rowtype;
  v_authorization {s}.banks_authorizations%rowtype;
  v_rule {s}.banks_authorization_rules%rowtype;
  v_authorizer uuid;
  v_balance_before numeric(14,2);
  v_balance_after numeric(14,2);
begin
  if p_decision not in ('aprobado','rechazado') then
    raise exception 'decision invalida';
  end if;
  if p_decided_by is null then
    raise exception 'decided_by requerido';
  end if;

  select * into v_movement
  from {s}.banks_movements
  where id = p_movement_id and empresa_id = p_empresa_id
  for update;
  if not found then
    raise exception 'movimiento no encontrado';
  end if;
  if v_movement.authorization_status <> 'pendiente' then
    raise exception 'movimiento ya decidido o no requiere autorizacion';
  end if;

  select * into v_authorization
  from {s}.banks_authorizations
  where id = v_movement.authorization_id
  for update;
  if not found then
    raise exception 'autorizacion no encontrada';
  end if;

  select * into v_rule
  from {s}.banks_authorization_rules
  where id = v_authorization.rule_id;

  v_authorizer := coalesce(v_rule.authorizer_user_id, p_default_authorizer);
  if v_authorizer is null then
    raise exception 'default_authorizer requerido';
  end if;
  if p_decided_by <> v_authorizer then
    raise exception 'usuario no autorizado para decidir';
  end if;

  if p_decision = 'rechazado' then
    update {s}.banks_authorizations
    set status = 'rechazado', decided_by = p_decided_by, decided_at = now(), decision_notes = p_decision_notes, updated_at = now()
    where id = v_authorization.id
    returning * into v_authorization;

    update {s}.banks_movements
    set authorization_status = 'rechazado', updated_at = now()
    where id = v_movement.id
    returning * into v_movement;

    return jsonb_build_object('ok', true, 'data', jsonb_build_object('movement', to_jsonb(v_movement), 'authorization', to_jsonb(v_authorization)));
  end if;

  select * into v_account
  from {s}.banks_accounts
  where id = v_movement.account_id
  for update;
  if not found then
    raise exception 'cuenta no encontrada';
  end if;

  v_balance_before := v_account.current_balance;
  v_balance_after := case when v_movement.movement_type = 'entrada' then v_account.current_balance + v_movement.amount else v_account.current_balance - v_movement.amount end;

  update {s}.banks_accounts
  set current_balance = v_balance_after, updated_at = now()
  where id = v_account.id;

  update {s}.banks_authorizations
  set status = 'aprobado', decided_by = p_decided_by, decided_at = now(), decision_notes = p_decision_notes, updated_at = now()
  where id = v_authorization.id
  returning * into v_authorization;

  update {s}.banks_movements
  set authorization_status = 'autorizado',
      balance_before = v_balance_before,
      balance_after = v_balance_after,
      updated_at = now()
  where id = v_movement.id
  returning * into v_movement;

  return jsonb_build_object(
    'ok', true,
    'data', jsonb_build_object(
      'movement', to_jsonb(v_movement),
      'authorization', to_jsonb(v_authorization),
      'balance_before', v_balance_before,
      'balance_after', v_balance_after
    )
  );
end;
$$;

create or replace function {s}.banks_movements_protect()
returns trigger language plpgsql as $$
declare
  v_old jsonb;
  v_new jsonb;
begin
  v_old := to_jsonb(old) - 'authorization_status' - 'authorization_id'
                          - 'balance_before' - 'balance_after'
                          - 'reconciliation_status' - 'reconciled_at'
                          - 'updated_at';
  v_new := to_jsonb(new) - 'authorization_status' - 'authorization_id'
                          - 'balance_before' - 'balance_after'
                          - 'reconciliation_status' - 'reconciled_at'
                          - 'updated_at';
  if v_old is distinct from v_new then
    raise exception 'banks_movements es inmutable salvo authorization_status/authorization_id/balance_before/balance_after/reconciliation_status/reconciled_at';
  end if;
  return new;
end;
$$;

drop trigger if exists banks_movements_protect_trg on {s}.banks_movements;
create trigger banks_movements_protect_trg
before update on {s}.banks_movements
for each row execute function {s}.banks_movements_protect();
"""
