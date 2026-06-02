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

-- Exponer schema en Data API
ALTER ROLE authenticator SET pgrst.db_schemas = 'public,storage,graphql_public,estoikolab,logplat,freelance,uc101_proy001,uc101_proy002,uc101_proy004';
NOTIFY pgrst, 'reload config';
NOTIFY pgrst, 'reload schema';
