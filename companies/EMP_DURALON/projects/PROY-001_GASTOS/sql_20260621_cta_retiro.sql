-- PROY-001_GASTOS: liga cada gasto a una cuenta de retiro de ERP Banks.
-- Seguro para ejecutar varias veces.

ALTER TABLE uc101_proy001.gastos
  ADD COLUMN IF NOT EXISTS cta_retiro_id     uuid NULL,
  ADD COLUMN IF NOT EXISTS cta_retiro_folio  text NULL,
  ADD COLUMN IF NOT EXISTS cta_retiro_nombre text NULL;

CREATE INDEX IF NOT EXISTS gastos_cta_retiro_id_idx
  ON uc101_proy001.gastos (cta_retiro_id);
