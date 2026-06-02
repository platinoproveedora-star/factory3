-- PROY-002_VENTAS migration 004
-- Agrega direccion de entrega por documento comercial.

ALTER TABLE uc101_proy002.sales_documents
  ADD COLUMN IF NOT EXISTS delivery_address text;

NOTIFY pgrst, 'reload schema';
