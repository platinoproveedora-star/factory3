-- Migration 003 - PROY-002 Ventas
-- PROY-002 usa clientes compartidos desde uc101_proy004.erp_parties.
-- Quita FKs locales legacy a sales_customers en tablas operativas.

ALTER TABLE uc101_proy002.sales_events
    DROP CONSTRAINT IF EXISTS sales_events_customer_id_fkey;

ALTER TABLE uc101_proy002.sales_payments
    DROP CONSTRAINT IF EXISTS sales_payments_customer_id_fkey;

ALTER TABLE uc101_proy002.sales_receivables
    DROP CONSTRAINT IF EXISTS sales_receivables_customer_id_fkey;

NOTIFY pgrst, 'reload schema';
