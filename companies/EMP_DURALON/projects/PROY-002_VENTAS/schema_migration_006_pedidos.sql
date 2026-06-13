-- PROY-002 Form02 Pedidos - campos para pedidos moviles y logistica futura
-- Ejecutar en Supabase sobre schema uc101_proy002.

ALTER TABLE uc101_proy002.sales_documents
    ADD COLUMN IF NOT EXISTS payment_method text,
    ADD COLUMN IF NOT EXISTS city text,
    ADD COLUMN IF NOT EXISTS city_quadrant text,
    ADD COLUMN IF NOT EXISTS total_weight_kg numeric(14,4) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS driver_name text,
    ADD COLUMN IF NOT EXISTS vehicle_name text;

ALTER TABLE uc101_proy002.sales_document_items
    ADD COLUMN IF NOT EXISTS unit_price_ex_vat numeric(14,4),
    ADD COLUMN IF NOT EXISTS vat_rate numeric(6,4),
    ADD COLUMN IF NOT EXISTS vat_amount numeric(14,4),
    ADD COLUMN IF NOT EXISTS unit_price_inc_vat numeric(14,4),
    ADD COLUMN IF NOT EXISTS line_subtotal numeric(14,4),
    ADD COLUMN IF NOT EXISTS weight_kg_per_unit numeric(14,4),
    ADD COLUMN IF NOT EXISTS weight_kg_total numeric(14,4),
    ADD COLUMN IF NOT EXISTS weight_source text NOT NULL DEFAULT 'missing';

CREATE INDEX IF NOT EXISTS idx_sales_documents_pedido_city
    ON uc101_proy002.sales_documents (empresa_id, document_type, city, city_quadrant);

CREATE INDEX IF NOT EXISTS idx_sales_documents_pedido_due_date
    ON uc101_proy002.sales_documents (empresa_id, document_type, due_date);
