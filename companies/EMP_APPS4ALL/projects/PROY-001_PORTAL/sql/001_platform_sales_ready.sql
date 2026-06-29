create schema if not exists platform;

create table if not exists platform.companies (
  company_id text primary key,
  name text not null,
  status text not null default 'active',
  stripe_customer_id text null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz null
);

create table if not exists platform.billing_accounts (
  id uuid primary key default gen_random_uuid(),
  company_id text not null references platform.companies(company_id),
  stripe_customer_id text null,
  default_plan_code text null,
  billing_email text null,
  status text not null default 'manual',
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz null
);

create table if not exists platform.company_users (
  id uuid primary key default gen_random_uuid(),
  company_id text not null references platform.companies(company_id),
  user_id uuid not null references platform.users(id),
  role text not null default 'member',
  status text not null default 'active',
  created_at timestamptz not null default now(),
  unique(company_id, user_id)
);

alter table platform.modulos
  add column if not exists app_url text null,
  add column if not exists icon text null,
  add column if not exists sort_order integer not null default 100,
  add column if not exists stripe_product_id text null,
  add column if not exists default_plan_code text null,
  add column if not exists metadata jsonb not null default '{}'::jsonb;

alter table platform.access_grants
  add column if not exists company_id text null,
  add column if not exists status text not null default 'manual',
  add column if not exists plan_code text null,
  add column if not exists subscription_status text not null default 'manual',
  add column if not exists stripe_subscription_id text null,
  add column if not exists stripe_price_id text null,
  add column if not exists current_period_end timestamptz null,
  add column if not exists metadata jsonb not null default '{}'::jsonb;

insert into platform.companies (company_id, name, status)
values
  ('EMP_APPS4ALL', 'Apps4All', 'active'),
  ('EMP_CONTA4ALL', 'Conta4All', 'active'),
  ('EMP_MULTI_SHOPPER', 'Multi Shopper', 'active'),
  ('EMP_DURALON', 'Duralon', 'active')
on conflict (company_id) do update set
  name = excluded.name,
  status = excluded.status,
  updated_at = now();

insert into platform.modulos (code, nombre, activo, app_url, icon, sort_order, default_plan_code)
values
  ('apps4all_portal', 'Apps4All Portal', true, null, 'layout-dashboard', 1, 'platform_free'),
  ('conta4all', 'Conta4All', true, 'https://conta4all-dashboard.vercel.app', 'file-spreadsheet', 10, 'conta4all_manual'),
  ('vertical_multi_shopper', 'Multi Shopper', true, 'https://emp-multi-shopper-dashboard.vercel.app', 'shopping-basket', 20, 'multi_shopper_manual'),
  ('gastos', 'Gastos', true, '/apps/gastos', 'receipt-text', 30, 'gastos_manual')
on conflict (code) do update set
  nombre = excluded.nombre,
  activo = excluded.activo,
  app_url = excluded.app_url,
  icon = excluded.icon,
  sort_order = excluded.sort_order,
  default_plan_code = excluded.default_plan_code;

update platform.access_grants
set company_id = case
  when modulo_code = 'conta4all' then 'EMP_CONTA4ALL'
  when modulo_code = 'vertical_multi_shopper' then 'EMP_MULTI_SHOPPER'
  when modulo_code = 'gastos' then 'EMP_DURALON'
  when modulo_code = 'apps4all_portal' then 'EMP_APPS4ALL'
  else coalesce(company_id, 'EMP_APPS4ALL')
end
where company_id is null;

update platform.access_grants
set
  status = coalesce(nullif(status, ''), 'manual'),
  subscription_status = coalesce(nullif(subscription_status, ''), status, 'manual'),
  plan_code = coalesce(plan_code, modulo_code || '_manual');

do $$
declare
  constraint_name text;
begin
  select conname into constraint_name
  from pg_constraint
  where conrelid = 'platform.access_grants'::regclass
    and contype = 'u'
    and pg_get_constraintdef(oid) like '%user_id%'
    and pg_get_constraintdef(oid) like '%modulo_code%'
    and pg_get_constraintdef(oid) not like '%company_id%'
  limit 1;

  if constraint_name is not null then
    execute format('alter table platform.access_grants drop constraint %I', constraint_name);
  end if;
end $$;

delete from platform.access_grants a
using platform.access_grants b
where a.ctid < b.ctid
  and a.user_id = b.user_id
  and coalesce(a.company_id, '') = coalesce(b.company_id, '')
  and a.modulo_code = b.modulo_code;

create unique index if not exists access_grants_user_company_module_uidx
on platform.access_grants (user_id, company_id, modulo_code);

insert into platform.company_users (company_id, user_id, role, status)
select distinct company_id, user_id, role, 'active'
from platform.access_grants
where company_id is not null
on conflict (company_id, user_id) do update set role = excluded.role, status = 'active';

insert into platform.access_grants (user_id, company_id, modulo_code, role, status, plan_code, subscription_status)
select distinct user_id, 'EMP_APPS4ALL', 'apps4all_portal',
  case when role = 'platform_admin' then 'platform_admin' else 'owner' end,
  'manual', 'platform_free', 'manual'
from platform.access_grants
where modulo_code <> 'apps4all_portal'
on conflict (user_id, company_id, modulo_code) do update set
  status = excluded.status,
  subscription_status = excluded.subscription_status;

insert into platform.access_grants (user_id, company_id, modulo_code, role, status, plan_code, subscription_status)
select distinct user_id, 'EMP_DURALON', 'gastos',
  case when role = 'platform_admin' then 'platform_admin' else 'owner' end,
  'manual', 'gastos_manual', 'manual'
from platform.access_grants
where role in ('owner', 'platform_admin')
on conflict (user_id, company_id, modulo_code) do update set
  status = excluded.status,
  subscription_status = excluded.subscription_status;

grant usage on schema platform to anon, authenticated, service_role;
grant select on platform.modulos to anon, authenticated;
grant all on platform.companies, platform.company_users, platform.billing_accounts to service_role;
grant select on platform.companies, platform.company_users, platform.access_grants to authenticated;

do $$
declare
  table_name text;
begin
  foreach table_name in array array[
    'users',
    'access_grants',
    'login_attempts',
    'password_resets',
    'secrets',
    'audit_log'
  ]
  loop
    if to_regclass('platform.' || table_name) is not null then
      execute format('grant all on platform.%I to service_role', table_name);
    end if;
  end loop;
end $$;

notify pgrst, 'reload schema';
