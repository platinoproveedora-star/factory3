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
    delivery_address text,
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

CREATE TABLE IF NOT EXISTS uc101_proy004.erp_folio_sequences (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    folio text UNIQUE NOT NULL,
    empresa_id text NOT NULL DEFAULT 'EMP_DURALON',
    project_code text NOT NULL DEFAULT 'PROY-004',
    module_code text NOT NULL DEFAULT 'inventario',
    scope text NOT NULL,
    prefix text NOT NULL,
    current_number integer NOT NULL DEFAULT 0,
    digits integer NOT NULL DEFAULT 5,
    erp_tags jsonb NOT NULL DEFAULT '{}',
    metadata jsonb NOT NULL DEFAULT '{}',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz,
    CONSTRAINT erp_folio_sequences_digits_check CHECK (digits BETWEEN 1 AND 12),
    CONSTRAINT erp_folio_sequences_current_check CHECK (current_number >= 0),
    CONSTRAINT erp_folio_sequences_scope_unique UNIQUE (empresa_id, project_code, module_code, scope, prefix)
);

CREATE OR REPLACE FUNCTION uc101_proy004.reserve_erp_folio(
    p_scope text,
    p_prefix text,
    p_digits integer DEFAULT 5,
    p_empresa_id text DEFAULT 'EMP_DURALON',
    p_project_code text DEFAULT 'PROY-004',
    p_module_code text DEFAULT 'inventario',
    p_min_current integer DEFAULT 0
)
RETURNS text
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = uc101_proy004, public
AS $$
DECLARE
    v_number integer;
    v_prefix text;
    v_scope text;
BEGIN
    v_prefix := upper(trim(p_prefix));
    v_scope := lower(trim(p_scope));

    IF v_prefix !~ '^[A-Z0-9_]{2,12}$' THEN
        RAISE EXCEPTION 'prefix invalido: %', p_prefix;
    END IF;
    IF v_scope !~ '^[a-z0-9_]{2,80}$' THEN
        RAISE EXCEPTION 'scope invalido: %', p_scope;
    END IF;
    IF p_digits IS NULL OR p_digits < 1 OR p_digits > 12 THEN
        RAISE EXCEPTION 'digits invalido: %', p_digits;
    END IF;
    IF p_min_current IS NULL OR p_min_current < 0 THEN
        p_min_current := 0;
    END IF;

    INSERT INTO uc101_proy004.erp_folio_sequences (
        folio,
        empresa_id,
        project_code,
        module_code,
        scope,
        prefix,
        current_number,
        digits
    )
    VALUES (
        'SEQ-' || upper(regexp_replace(coalesce(p_module_code, 'erp'), '[^A-Za-z0-9]+', '_', 'g')) || '-' || v_scope || '-' || v_prefix,
        p_empresa_id,
        p_project_code,
        p_module_code,
        v_scope,
        v_prefix,
        p_min_current,
        p_digits
    )
    ON CONFLICT (empresa_id, project_code, module_code, scope, prefix) DO NOTHING;

    UPDATE uc101_proy004.erp_folio_sequences
    SET current_number = greatest(current_number, p_min_current) + 1,
        digits = p_digits,
        updated_at = now()
    WHERE empresa_id = p_empresa_id
      AND project_code = p_project_code
      AND module_code = p_module_code
      AND scope = v_scope
      AND prefix = v_prefix
    RETURNING current_number INTO v_number;

    RETURN v_prefix || '-' || lpad(v_number::text, p_digits, '0');
END;
$$;

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

CREATE INDEX IF NOT EXISTS idx_erp_folio_sequences_scope
    ON uc101_proy004.erp_folio_sequences (empresa_id, project_code, module_code, scope, prefix);
