-- PROY-002_VENTAS - lotes y snapshots de costo en renglones de venta
-- Idempotente: puede ejecutarse mas de una vez.

alter table uc101_proy002.sales_document_items
    add column if not exists lot_code text,
    add column if not exists lot_cost_snapshot numeric(14,2),
    add column if not exists avg_cost_snapshot numeric(14,2),
    add column if not exists last_cost_snapshot numeric(14,2);

create index if not exists idx_sales_document_items_lot
    on uc101_proy002.sales_document_items (inventory_product_id, lot_code);

notify pgrst, 'reload schema';
