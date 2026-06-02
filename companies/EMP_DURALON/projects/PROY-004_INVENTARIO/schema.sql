-- ============================================================
-- PROY-004_INVENTARIO - Duralon
-- Schema: uc101_proy004
-- ERP identity: EMP_DURALON / PROY-004 / inventario
-- Draft: revisar antes de ejecutar en Supabase
-- ============================================================

CREATE SCHEMA IF NOT EXISTS uc101_proy004;

CREATE TABLE IF NOT EXISTS uc101_proy004.erp_products (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    folio text UNIQUE NOT NULL,
    empresa_id text NOT NULL DEFAULT 'EMP_DURALON',
    project_code text NOT NULL DEFAULT 'PROY-004',
    module_code text NOT NULL DEFAULT 'inventario',
    product_key text,
    product_name text NOT NULL,
    sku text,
    category text,
    unit text NOT NULL DEFAULT 'pieza',
    active boolean NOT NULL DEFAULT true,
    is_key_product boolean NOT NULL DEFAULT false,
    min_stock numeric(14,4) NOT NULL DEFAULT 0,
    erp_tags jsonb NOT NULL DEFAULT '{}',
    metadata jsonb NOT NULL DEFAULT '{}',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz
);

CREATE TABLE IF NOT EXISTS uc101_proy004.erp_parties (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    folio text UNIQUE NOT NULL,
    empresa_id text NOT NULL DEFAULT 'EMP_DURALON',
    project_code text NOT NULL DEFAULT 'PROY-004',
    module_code text NOT NULL DEFAULT 'inventario',
    party_type text NOT NULL CHECK (party_type IN ('customer', 'supplier', 'both')),
    party_name text NOT NULL,
    legal_name text,
    rfc text,
    phone text,
    email text,
    address text,
    active boolean NOT NULL DEFAULT true,
    erp_tags jsonb NOT NULL DEFAULT '{}',
    metadata jsonb NOT NULL DEFAULT '{}',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz
);

CREATE TABLE IF NOT EXISTS uc101_proy004.erp_kardex (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    folio text UNIQUE NOT NULL,
    empresa_id text NOT NULL DEFAULT 'EMP_DURALON',
    project_code text NOT NULL DEFAULT 'PROY-004',
    module_code text NOT NULL DEFAULT 'inventario',
    movement_type text NOT NULL CHECK (movement_type IN ('entrada', 'salida', 'ajuste', 'devolucion')),
    source_type text NOT NULL CHECK (source_type IN ('compra', 'remision', 'ajuste', 'devolucion')),
    source_folio text,
    external_folio text,
    purchase_folio text,
    remission_folio text,
    quote_folio text,
    order_folio text,
    invoice_folio text,
    product_id uuid NOT NULL REFERENCES uc101_proy004.erp_products(id),
    product_name_snapshot text,
    customer_id uuid REFERENCES uc101_proy004.erp_parties(id),
    customer_name_snapshot text,
    supplier_id uuid REFERENCES uc101_proy004.erp_parties(id),
    supplier_name_snapshot text,
    movement_date date NOT NULL DEFAULT CURRENT_DATE,
    quantity_in numeric(14,4) NOT NULL DEFAULT 0,
    quantity_out numeric(14,4) NOT NULL DEFAULT 0,
    balance_after numeric(14,4) NOT NULL DEFAULT 0,
    unit_cost numeric(14,2),
    unit_price numeric(14,2),
    total_cost numeric(14,2) NOT NULL DEFAULT 0,
    total_sale numeric(14,2) NOT NULL DEFAULT 0,
    payment_status text NOT NULL DEFAULT 'pendiente',
    paid_amount numeric(14,2) NOT NULL DEFAULT 0,
    balance_amount numeric(14,2) NOT NULL DEFAULT 0,
    notes text,
    created_by_user_id uuid,
    erp_tags jsonb NOT NULL DEFAULT '{}',
    metadata jsonb NOT NULL DEFAULT '{}',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz,
    CONSTRAINT erp_kardex_quantity_direction CHECK (
        (movement_type = 'entrada' AND quantity_in > 0 AND quantity_out = 0)
        OR (movement_type = 'salida' AND quantity_out > 0 AND quantity_in = 0)
        OR (movement_type IN ('ajuste', 'devolucion'))
    )
);

CREATE TABLE IF NOT EXISTS uc101_proy004.erp_recurrence_rules (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    folio text UNIQUE NOT NULL,
    empresa_id text NOT NULL DEFAULT 'EMP_DURALON',
    project_code text NOT NULL DEFAULT 'PROY-004',
    module_code text NOT NULL DEFAULT 'inventario',
    product_key text NOT NULL,
    product_name text NOT NULL,
    threshold_days integer NOT NULL DEFAULT 7,
    alert_frequency text NOT NULL DEFAULT 'daily',
    active boolean NOT NULL DEFAULT true,
    erp_tags jsonb NOT NULL DEFAULT '{}',
    metadata jsonb NOT NULL DEFAULT '{}',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz
);

CREATE INDEX IF NOT EXISTS idx_erp_products_key
    ON uc101_proy004.erp_products (empresa_id, product_key);

CREATE INDEX IF NOT EXISTS idx_erp_parties_type
    ON uc101_proy004.erp_parties (empresa_id, party_type, active);

CREATE INDEX IF NOT EXISTS idx_erp_kardex_product_date
    ON uc101_proy004.erp_kardex (product_id, movement_date);

CREATE INDEX IF NOT EXISTS idx_erp_kardex_customer_date
    ON uc101_proy004.erp_kardex (customer_id, movement_date);

CREATE INDEX IF NOT EXISTS idx_erp_kardex_source
    ON uc101_proy004.erp_kardex (source_type, source_folio);

