-- PROY-004_INVENTARIO migration 001
-- Agrega direccion de entrega al kardex para salidas por remision.

ALTER TABLE uc101_proy004.erp_kardex
  ADD COLUMN IF NOT EXISTS delivery_address text;

NOTIFY pgrst, 'reload schema';
