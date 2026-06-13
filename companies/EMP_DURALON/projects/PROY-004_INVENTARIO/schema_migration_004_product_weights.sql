-- PROY-004 Inventario - equivalencia de peso por producto
-- Ejecutar en Supabase sobre schema uc101_proy004.

ALTER TABLE uc101_proy004.erp_products
    ADD COLUMN IF NOT EXISTS weight_kg numeric(14,4),
    ADD COLUMN IF NOT EXISTS weight_unit text NOT NULL DEFAULT 'kg',
    ADD COLUMN IF NOT EXISTS weight_notes text;

CREATE INDEX IF NOT EXISTS idx_erp_products_weight_missing
    ON uc101_proy004.erp_products (empresa_id, active)
    WHERE weight_kg IS NULL;
