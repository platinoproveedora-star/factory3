-- PROY-007 Bank Statement Converter
-- Ejecutar con supabase_sql_execute en schema: uc101_proy007
-- Crear schema primero si no existe:
-- CREATE SCHEMA IF NOT EXISTS uc101_proy007;

create table if not exists uc101_proy007.statement_extractions (
  id uuid primary key default gen_random_uuid(),
  folio text unique not null,
  empresa_id text not null,
  project_code text not null,
  module_code text not null default 'bank_statement_converter',

  source_format text not null
    constraint statement_extractions_source_format_chk
    check (source_format in ('pdf','csv','txt')),

  bank_profile text not null,
  profile_version text not null default 'v1',
  bank_name text,

  account_number_mask text,
  statement_period_start date,
  statement_period_end date,

  file_name text,
  file_hash text not null,
  file_size_bytes bigint,
  mime_type text,

  storage_bucket text,
  storage_path text,

  total_lines_raw integer not null default 0,
  total_blocks_detected integer not null default 0,
  total_lines_extracted integer not null default 0,

  total_deposits_reported numeric(14,2),
  total_deposits_extracted numeric(14,2),
  validation_diff_deposits numeric(14,2),

  total_withdrawals_reported numeric(14,2),
  total_withdrawals_extracted numeric(14,2),
  validation_diff_withdrawals numeric(14,2),

  validation_status text not null default 'pendiente'
    constraint statement_extractions_validation_status_chk
    check (validation_status in ('pendiente','validado','con_diferencias','no_validable')),

  status text not null default 'extraido'
    constraint statement_extractions_status_chk
    check (status in ('extraido','con_errores','requires_ocr')),

  warnings jsonb not null default '[]',
  metadata jsonb not null default '{}',

  created_at timestamptz not null default now(),
  updated_at timestamptz
);

create unique index if not exists statement_extractions_file_unique_idx
  on uc101_proy007.statement_extractions(bank_profile, file_hash);

create index if not exists statement_extractions_empresa_idx
  on uc101_proy007.statement_extractions(empresa_id, project_code);

create index if not exists statement_extractions_period_idx
  on uc101_proy007.statement_extractions(statement_period_start, statement_period_end);

create index if not exists statement_extractions_status_idx
  on uc101_proy007.statement_extractions(status, validation_status);


create table if not exists uc101_proy007.statement_extracted_lines (
  id uuid primary key default gen_random_uuid(),
  folio text unique not null,
  empresa_id text not null,
  project_code text not null,
  module_code text not null default 'bank_statement_converter',

  extraction_id uuid not null references uc101_proy007.statement_extractions(id),

  raw_line_order integer not null,

  transaction_date date,
  posting_date date,
  line_date date not null,

  description text,

  direction text not null
    constraint statement_extracted_lines_direction_chk
    check (direction in ('deposito','retiro')),

  amount numeric(14,2) not null,
  saldo numeric(14,2),

  clave_rastreo text,
  referencia text,

  confidence numeric(5,4) not null default 1.0000,
  parse_warnings jsonb not null default '[]',

  raw_text text not null,
  metadata jsonb not null default '{}',

  created_at timestamptz not null default now()
);

create index if not exists idx_bsl_extraction
  on uc101_proy007.statement_extracted_lines(extraction_id);

create index if not exists idx_bsl_rastreo
  on uc101_proy007.statement_extracted_lines(clave_rastreo);

create index if not exists idx_bsl_referencia
  on uc101_proy007.statement_extracted_lines(referencia);

create index if not exists idx_bsl_dates
  on uc101_proy007.statement_extracted_lines(line_date, posting_date, transaction_date);

create index if not exists idx_bsl_amount
  on uc101_proy007.statement_extracted_lines(amount);
