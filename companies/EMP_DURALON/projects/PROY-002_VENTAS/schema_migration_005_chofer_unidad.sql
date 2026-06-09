-- PROY-002_VENTAS migration 005
-- Agrega datos logisticos opcionales al encabezado de remisiones.

alter table uc101_proy002.sales_documents
  add column if not exists chofer text,
  add column if not exists unidad text;

create index if not exists idx_sales_documents_chofer
  on uc101_proy002.sales_documents (empresa_id, document_type, chofer);

create index if not exists idx_sales_documents_unidad
  on uc101_proy002.sales_documents (empresa_id, document_type, unidad);

notify pgrst, 'reload schema';
