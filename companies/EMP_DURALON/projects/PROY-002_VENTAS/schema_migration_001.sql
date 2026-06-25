-- Migration 001 — PROY-002 Ventas
-- Agrega snapshot fields a sales_documents
-- customer_id apunta a uc101_proy004.erp_parties (sin FK cross-schema)

ALTER TABLE uc101_proy002.sales_documents
    ALTER COLUMN customer_id DROP DEFAULT;

-- Eliminar FK a sales_customers si existe
ALTER TABLE uc101_proy002.sales_documents
    DROP CONSTRAINT IF EXISTS sales_documents_customer_id_fkey;

-- Agregar campos snapshot
ALTER TABLE uc101_proy002.sales_documents
    ADD COLUMN IF NOT EXISTS customer_name_snapshot text,
    ADD COLUMN IF NOT EXISTS customer_folio_snapshot text;

-- PASO FINAL OBLIGATORIO: exponer schema en Data API (PostgREST)
-- NO ejecutar ALTER ROLE manualmente — sobrescribiría otros schemas expuestos.
-- Usar el skill:
--   supabase_expose_schema  { "schema": "uc101_proy002", "dry_run": false }
-- El skill hace append seguro sin tocar schemas existentes.
