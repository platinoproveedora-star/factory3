-- Migration 002 - PROY-002 Ventas
-- Permite que sales_document_items use product_id del catalogo compartido
-- uc101_proy004.erp_products. No se puede usar FK cross-schema por REST,
-- asi que se guarda snapshot y metadata de integracion.

ALTER TABLE uc101_proy002.sales_document_items
    DROP CONSTRAINT IF EXISTS sales_document_items_product_id_fkey;

ALTER TABLE uc101_proy002.sales_document_items
    ADD COLUMN IF NOT EXISTS product_folio_snapshot text,
    ADD COLUMN IF NOT EXISTS product_name_snapshot text,
    ADD COLUMN IF NOT EXISTS inventory_schema text NOT NULL DEFAULT 'uc101_proy004',
    ADD COLUMN IF NOT EXISTS inventory_product_id uuid;

NOTIFY pgrst, 'reload schema';
