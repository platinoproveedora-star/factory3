-- FLEET4ALL schema v1 — multi-tenant por empresa_id
-- Base: logplat en producción, traducido y generalizado.
-- NO EJECUTAR hasta aprobación de Ach. Exponer con supabase_expose_schema.
create schema if not exists fleet4all;

-- ============ COMPARTIDAS (todos los módulos) ============
create table if not exists fleet4all.units (
  id uuid primary key default gen_random_uuid(),
  empresa_id text not null,
  unit_key text not null,
  plate text, brand text, model text, year int,
  unit_type text default 'tractor',        -- tractor|trailer|van|pickup
  odometer_km numeric(12,1) default 0,
  status text default 'active',
  created_at timestamptz default now(), updated_at timestamptz default now(),
  unique (empresa_id, unit_key)
);
create table if not exists fleet4all.drivers (
  id uuid primary key default gen_random_uuid(),
  empresa_id text not null,
  driver_key text not null,
  full_name text not null, phone text,
  license_number text, license_expiry date,
  pay_scheme text default 'per_trip',      -- per_trip|salary|percent
  pay_rate numeric(12,2),
  status text default 'active',
  created_at timestamptz default now(), updated_at timestamptz default now(),
  unique (empresa_id, driver_key)
);

-- ============ TRIPS4ALL ============
create table if not exists fleet4all.trips (
  id uuid primary key default gen_random_uuid(),
  empresa_id text not null,
  trip_folio text not null,
  customer text, origin text, destination text,
  departure_date date, arrival_date date,
  trip_cost numeric(12,2) default 0,
  sale_price numeric(12,2) default 0,
  trip_profit numeric(12,2) default 0,
  currency text default 'MXN',
  driver_key text, unit_key text,
  distance_km numeric(10,1),
  trip_status text default 'active',        -- active|closed|canceled
  payment_status text default 'receivable', -- receivable|partial|paid
  doc_id text,
  created_at timestamptz default now(), updated_at timestamptz default now(),
  unique (empresa_id, trip_folio)
);
create table if not exists fleet4all.expenses (
  id uuid primary key default gen_random_uuid(),
  empresa_id text not null,
  expense_folio text not null,
  trip_folio text,
  expense_date date, captured_at timestamptz default now(),
  amount numeric(12,2) default 0, currency text default 'MXN',
  concept text,
  expense_type text,                        -- fuel|tolls|food|repair|other
  driver_key text, doc_id text,
  created_at timestamptz default now(), updated_at timestamptz default now(),
  unique (empresa_id, expense_folio)
);
create table if not exists fleet4all.trip_docs (
  id uuid primary key default gen_random_uuid(),
  empresa_id text not null,
  doc_folio text not null, trip_folio text not null,
  doc_url text not null,
  doc_type text default 'other',            -- bol|invoice|ticket|photo|cartaporte|other
  name text,
  created_at timestamptz default now(),
  unique (empresa_id, doc_folio)
);

-- ============ COLLECT4ALL ============
create table if not exists fleet4all.payments (
  id uuid primary key default gen_random_uuid(),
  empresa_id text not null,
  payment_folio text not null,
  trip_folio text, customer text,
  payment_date date,
  amount numeric(12,2) default 0, currency text default 'MXN',
  method text default 'transfer',           -- transfer|cash|check|card
  tracking_key text, notes text, doc_id text,
  created_at timestamptz default now(), updated_at timestamptz default now(),
  unique (empresa_id, payment_folio)
);
create table if not exists fleet4all.receivables (
  id uuid primary key default gen_random_uuid(),
  empresa_id text not null,
  receivable_folio text not null,
  trip_folio text, customer text,
  total_amount numeric(12,2) default 0,
  paid_amount numeric(12,2) default 0,
  balance numeric(12,2) default 0,
  currency text default 'MXN',
  trip_date date, due_date date,
  collection_status text default 'pending', -- pending|partial|paid|overdue
  created_at timestamptz default now(), updated_at timestamptz default now(),
  unique (empresa_id, receivable_folio)
);

-- ============ CARTAPORTE4ALL ============
create table if not exists fleet4all.cartaporte_stamps (
  id uuid primary key default gen_random_uuid(),
  empresa_id text not null,
  stamp_folio text not null,
  trip_folio text not null,
  cfdi_type text default 'traslado',        -- traslado|ingreso
  uuid_sat text,
  xml_path text, pdf_path text,
  pac_provider text,                        -- sw|facturama|finkok
  stamp_status text default 'draft',        -- draft|stamped|canceled|error
  error_detail text,
  stamped_at timestamptz,
  created_at timestamptz default now(), updated_at timestamptz default now(),
  unique (empresa_id, stamp_folio)
);
create table if not exists fleet4all.fiscal_credentials (
  id uuid primary key default gen_random_uuid(),
  empresa_id text not null,
  rfc text not null,
  csd_cer_encrypted text, csd_key_encrypted text,
  key_password_encrypted text,
  kek_version int default 1,                -- patrón envelope de Conta4all
  valid_until date,
  status text default 'active',
  created_at timestamptz default now(), updated_at timestamptz default now(),
  unique (empresa_id, rfc)
);

-- ============ SETTLEMENTS4ALL ============
create table if not exists fleet4all.settlements (
  id uuid primary key default gen_random_uuid(),
  empresa_id text not null,
  settlement_folio text not null,
  driver_key text not null,
  period_from date, period_to date,
  trips_included jsonb,                     -- ["T-0025","T-0026"]
  gross_amount numeric(12,2) default 0,
  advances_deducted numeric(12,2) default 0,
  other_deductions numeric(12,2) default 0,
  net_amount numeric(12,2) default 0,
  currency text default 'MXN',
  status text default 'draft',              -- draft|approved|paid
  receipt_pdf_path text,
  created_at timestamptz default now(), updated_at timestamptz default now(),
  unique (empresa_id, settlement_folio)
);
create table if not exists fleet4all.driver_advances (
  id uuid primary key default gen_random_uuid(),
  empresa_id text not null,
  advance_folio text not null,
  driver_key text not null,
  advance_date date,
  amount numeric(12,2) default 0, currency text default 'MXN',
  concept text, trip_folio text,
  settled_in text,                          -- settlement_folio o null
  created_at timestamptz default now(), updated_at timestamptz default now(),
  unique (empresa_id, advance_folio)
);

-- ============ FUEL4ALL ============
create table if not exists fleet4all.fuel_loads (
  id uuid primary key default gen_random_uuid(),
  empresa_id text not null,
  fuel_folio text not null,
  unit_key text not null, driver_key text, trip_folio text,
  load_date date,
  liters numeric(10,2) default 0,
  amount numeric(12,2) default 0, currency text default 'MXN',
  price_per_liter numeric(8,3),
  odometer_km numeric(12,1),
  station text, doc_id text,
  created_at timestamptz default now(), updated_at timestamptz default now(),
  unique (empresa_id, fuel_folio)
);
create table if not exists fleet4all.fuel_efficiency (
  id uuid primary key default gen_random_uuid(),
  empresa_id text not null,
  unit_key text not null,
  period_from date, period_to date,
  km_traveled numeric(12,1), liters_loaded numeric(12,2),
  km_per_liter numeric(8,3),
  expected_km_per_liter numeric(8,3),
  deviation_pct numeric(6,2),
  flag text default 'ok',                   -- ok|warning|alert
  created_at timestamptz default now(), updated_at timestamptz default now(),
  unique (empresa_id, unit_key, period_from, period_to)
);

-- ============ MAINTENANCE4ALL ============
create table if not exists fleet4all.maintenance_plans (
  id uuid primary key default gen_random_uuid(),
  empresa_id text not null,
  plan_folio text not null,
  unit_key text not null,
  service_type text not null,               -- oil|brakes|tires|inspection|other
  every_km numeric(12,1), every_days int,
  last_service_km numeric(12,1), last_service_date date,
  next_due_km numeric(12,1), next_due_date date,
  status text default 'active',
  created_at timestamptz default now(), updated_at timestamptz default now(),
  unique (empresa_id, plan_folio)
);
create table if not exists fleet4all.services (
  id uuid primary key default gen_random_uuid(),
  empresa_id text not null,
  service_folio text not null,
  unit_key text not null, plan_folio text,
  service_date date, odometer_km numeric(12,1),
  service_type text, description text,
  cost numeric(12,2) default 0, currency text default 'MXN',
  workshop text, doc_id text,
  created_at timestamptz default now(), updated_at timestamptz default now(),
  unique (empresa_id, service_folio)
);
create table if not exists fleet4all.parts (
  id uuid primary key default gen_random_uuid(),
  empresa_id text not null,
  part_key text not null,
  name text not null, unit_measure text default 'pza',
  stock numeric(12,2) default 0, min_stock numeric(12,2) default 0,
  avg_cost numeric(12,2) default 0, currency text default 'MXN',
  created_at timestamptz default now(), updated_at timestamptz default now(),
  unique (empresa_id, part_key)
);
create table if not exists fleet4all.part_movements (
  id uuid primary key default gen_random_uuid(),
  empresa_id text not null,
  movement_folio text not null,
  part_key text not null,
  movement_type text not null,              -- in|out
  quantity numeric(12,2) not null,
  service_folio text, unit_key text,
  movement_date date, notes text,
  created_at timestamptz default now(),
  unique (empresa_id, movement_folio)
);

-- ============ QUOTES4ALL ============
create table if not exists fleet4all.rates (
  id uuid primary key default gen_random_uuid(),
  empresa_id text not null,
  rate_key text not null,
  origin text, destination text,
  cargo_type text, unit_type text,
  base_price numeric(12,2), price_per_km numeric(10,2),
  price_per_ton numeric(10,2),
  currency text default 'MXN',
  status text default 'active',
  created_at timestamptz default now(), updated_at timestamptz default now(),
  unique (empresa_id, rate_key)
);
create table if not exists fleet4all.quotes (
  id uuid primary key default gen_random_uuid(),
  empresa_id text not null,
  quote_folio text not null,
  customer text, origin text, destination text,
  cargo_type text, weight_tons numeric(10,2), distance_km numeric(10,1),
  quoted_price numeric(12,2), currency text default 'MXN',
  valid_until date,
  status text default 'sent',               -- draft|sent|accepted|rejected|expired
  trip_folio text,                          -- si se convirtió en viaje
  pdf_path text,
  created_at timestamptz default now(), updated_at timestamptz default now(),
  unique (empresa_id, quote_folio)
);

-- ============ LOADS4ALL (fase 2 — tablas desde v1 para no migrar) ============
create table if not exists fleet4all.loads (
  id uuid primary key default gen_random_uuid(),
  load_folio text not null unique,
  publisher_empresa_id text not null,
  origin text not null, destination text not null,
  cargo_type text, weight_tons numeric(10,2),
  pickup_date date, offered_price numeric(12,2), currency text default 'MXN',
  requirements text,
  status text default 'open',               -- open|matched|in_transit|done|canceled
  matched_empresa_id text, matched_trip_folio text,
  created_at timestamptz default now(), updated_at timestamptz default now()
);
