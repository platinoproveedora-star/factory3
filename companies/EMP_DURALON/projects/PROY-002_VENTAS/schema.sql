-- ============================================================
-- PROY-002_VENTAS - Duralon
-- Schema: uc101_proy002
-- ERP identity: EMP_DURALON / PROY-002 / ventas
-- Draft: revisar antes de ejecutar en Supabase
-- ============================================================

CREATE SCHEMA IF NOT EXISTS uc101_proy002;

-- Clientes
CREATE TABLE IF NOT EXISTS uc101_proy002.sales_customers (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    folio text UNIQUE NOT NULL,
    empresa_id text NOT NULL DEFAULT 'EMP_DURALON',
    project_code text NOT NULL DEFAULT 'PROY-002',
    module_code text NOT NULL DEFAULT 'ventas',
    customer_name text NOT NULL,
    legal_name text,
    rfc text,
    phone text,
    email text,
    address text,
    status text NOT NULL DEFAULT 'active',
    credit_days integer NOT NULL DEFAULT 0,
    credit_limit numeric(14,2) NOT NULL DEFAULT 0,
    notes text,
    erp_tags jsonb NOT NULL DEFAULT '{}',
    metadata jsonb NOT NULL DEFAULT '{}',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz
);

-- Productos / conceptos
CREATE TABLE IF NOT EXISTS uc101_proy002.sales_products (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    folio text UNIQUE NOT NULL,
    empresa_id text NOT NULL DEFAULT 'EMP_DURALON',
    project_code text NOT NULL DEFAULT 'PROY-002',
    module_code text NOT NULL DEFAULT 'ventas',
    product_name text NOT NULL,
    sku text,
    category text,
    unit text NOT NULL DEFAULT 'pieza',
    unit_price numeric(14,2) NOT NULL DEFAULT 0,
    unit_cost numeric(14,2),
    tax_rate numeric(6,4) NOT NULL DEFAULT 0,
    active boolean NOT NULL DEFAULT true,
    notes text,
    erp_tags jsonb NOT NULL DEFAULT '{}',
    metadata jsonb NOT NULL DEFAULT '{}',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz
);

-- Documentos comerciales: cotizacion, pedido, remision, factura
CREATE TABLE IF NOT EXISTS uc101_proy002.sales_documents (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    folio text UNIQUE NOT NULL,
    empresa_id text NOT NULL DEFAULT 'EMP_DURALON',
    project_code text NOT NULL DEFAULT 'PROY-002',
    module_code text NOT NULL DEFAULT 'ventas',
    document_type text NOT NULL CHECK (document_type IN ('cotizacion', 'pedido', 'remision', 'factura')),
    external_folio text,
    customer_id uuid REFERENCES uc101_proy002.sales_customers(id),
    delivery_address text,
    chofer text,
    unidad text,
    parent_document_id uuid REFERENCES uc101_proy002.sales_documents(id),
    root_document_id uuid REFERENCES uc101_proy002.sales_documents(id),
    status text NOT NULL DEFAULT 'draft',
    document_date date NOT NULL DEFAULT CURRENT_DATE,
    due_date date,
    valid_until date,
    currency text NOT NULL DEFAULT 'MXN',
    subtotal numeric(14,2) NOT NULL DEFAULT 0,
    discount_total numeric(14,2) NOT NULL DEFAULT 0,
    tax_total numeric(14,2) NOT NULL DEFAULT 0,
    total numeric(14,2) NOT NULL DEFAULT 0,
    paid_total numeric(14,2) NOT NULL DEFAULT 0,
    balance_total numeric(14,2) NOT NULL DEFAULT 0,
    created_by_user_id uuid,
    notes text,
    erp_tags jsonb NOT NULL DEFAULT '{}',
    metadata jsonb NOT NULL DEFAULT '{}',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz,
    CONSTRAINT sales_documents_external_folio_rule CHECK (
        document_type <> 'cotizacion' OR external_folio IS NULL
    )
);

-- Items de documentos comerciales
CREATE TABLE IF NOT EXISTS uc101_proy002.sales_document_items (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    folio text UNIQUE NOT NULL,
    empresa_id text NOT NULL DEFAULT 'EMP_DURALON',
    project_code text NOT NULL DEFAULT 'PROY-002',
    module_code text NOT NULL DEFAULT 'ventas',
    document_id uuid NOT NULL REFERENCES uc101_proy002.sales_documents(id),
    product_id uuid REFERENCES uc101_proy002.sales_products(id),
    description text NOT NULL,
    quantity numeric(14,4) NOT NULL DEFAULT 1,
    unit text NOT NULL DEFAULT 'pieza',
    unit_price numeric(14,2) NOT NULL DEFAULT 0,
    unit_cost numeric(14,2),
    lot_code text,
    lot_cost_snapshot numeric(14,2),
    avg_cost_snapshot numeric(14,2),
    last_cost_snapshot numeric(14,2),
    discount_amount numeric(14,2) NOT NULL DEFAULT 0,
    tax_rate numeric(6,4) NOT NULL DEFAULT 0,
    tax_amount numeric(14,2) NOT NULL DEFAULT 0,
    line_total numeric(14,2) NOT NULL DEFAULT 0,
    erp_tags jsonb NOT NULL DEFAULT '{}',
    metadata jsonb NOT NULL DEFAULT '{}',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz
);

-- Pagos recibidos
CREATE TABLE IF NOT EXISTS uc101_proy002.sales_payments (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    folio text UNIQUE NOT NULL,
    empresa_id text NOT NULL DEFAULT 'EMP_DURALON',
    project_code text NOT NULL DEFAULT 'PROY-002',
    module_code text NOT NULL DEFAULT 'ventas',
    customer_id uuid REFERENCES uc101_proy002.sales_customers(id),
    document_id uuid REFERENCES uc101_proy002.sales_documents(id),
    payment_date date NOT NULL DEFAULT CURRENT_DATE,
    amount numeric(14,2) NOT NULL,
    payment_method text NOT NULL DEFAULT 'transferencia',
    reference text,
    notes text,
    erp_tags jsonb NOT NULL DEFAULT '{}',
    metadata jsonb NOT NULL DEFAULT '{}',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz
);

-- Cuentas por cobrar
CREATE TABLE IF NOT EXISTS uc101_proy002.sales_receivables (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    folio text UNIQUE NOT NULL,
    empresa_id text NOT NULL DEFAULT 'EMP_DURALON',
    project_code text NOT NULL DEFAULT 'PROY-002',
    module_code text NOT NULL DEFAULT 'ventas',
    customer_id uuid NOT NULL REFERENCES uc101_proy002.sales_customers(id),
    document_id uuid REFERENCES uc101_proy002.sales_documents(id),
    document_folio text,
    issue_date date NOT NULL DEFAULT CURRENT_DATE,
    due_date date,
    total_amount numeric(14,2) NOT NULL DEFAULT 0,
    paid_amount numeric(14,2) NOT NULL DEFAULT 0,
    balance_amount numeric(14,2) NOT NULL DEFAULT 0,
    status text NOT NULL DEFAULT 'pendiente',
    notes text,
    erp_tags jsonb NOT NULL DEFAULT '{}',
    metadata jsonb NOT NULL DEFAULT '{}',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz
);

-- Eventos de ventas para auditoria e integracion cross-module
CREATE TABLE IF NOT EXISTS uc101_proy002.sales_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    folio text UNIQUE NOT NULL,
    empresa_id text NOT NULL DEFAULT 'EMP_DURALON',
    project_code text NOT NULL DEFAULT 'PROY-002',
    module_code text NOT NULL DEFAULT 'ventas',
    event_type text NOT NULL,
    document_id uuid REFERENCES uc101_proy002.sales_documents(id),
    customer_id uuid REFERENCES uc101_proy002.sales_customers(id),
    payload jsonb NOT NULL DEFAULT '{}',
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_sales_customers_empresa_status
    ON uc101_proy002.sales_customers (empresa_id, status);

CREATE INDEX IF NOT EXISTS idx_sales_documents_type_status
    ON uc101_proy002.sales_documents (empresa_id, document_type, status);

CREATE INDEX IF NOT EXISTS idx_sales_documents_customer
    ON uc101_proy002.sales_documents (customer_id, document_date);

CREATE INDEX IF NOT EXISTS idx_sales_document_items_document
    ON uc101_proy002.sales_document_items (document_id);

CREATE INDEX IF NOT EXISTS idx_sales_payments_document
    ON uc101_proy002.sales_payments (document_id, payment_date);

CREATE INDEX IF NOT EXISTS idx_sales_receivables_customer_status
    ON uc101_proy002.sales_receivables (customer_id, status);

CREATE INDEX IF NOT EXISTS idx_sales_events_document
    ON uc101_proy002.sales_events (document_id, created_at);
