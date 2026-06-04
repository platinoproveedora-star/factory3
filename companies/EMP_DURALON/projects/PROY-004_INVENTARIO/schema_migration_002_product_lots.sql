-- PROY-004_INVENTARIO - producto clasificacion y lotes
-- Idempotente: puede ejecutarse mas de una vez.

alter table uc101_proy004.erp_products
    add column if not exists category_2 text,
    add column if not exists brand text;

alter table uc101_proy004.erp_kardex
    add column if not exists lot_code text;

create index if not exists idx_erp_kardex_product_lot
    on uc101_proy004.erp_kardex (product_id, lot_code);

notify pgrst, 'reload schema';
