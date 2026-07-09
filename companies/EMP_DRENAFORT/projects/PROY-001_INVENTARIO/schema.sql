-- ============================================================
-- PROY-001_INVENTARIO - Drenafort
-- Schema: drenafort_proy001
-- ERP identity: EMP_DRENAFORT / PROY-001 / inventario
-- Mismo patron que uc101_proy004 (Duralon), con costo_unitario
-- propio en erp_products porque este catalogo nace de una lista
-- de precios (no hay tabla de compras/kardex todavia).
-- ============================================================

CREATE SCHEMA IF NOT EXISTS drenafort_proy001;

CREATE TABLE IF NOT EXISTS drenafort_proy001.erp_products (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    folio text UNIQUE NOT NULL,
    empresa_id text NOT NULL DEFAULT 'EMP_DRENAFORT',
    project_code text NOT NULL DEFAULT 'PROY-001',
    module_code text NOT NULL DEFAULT 'inventario',
    product_key text,
    product_name text NOT NULL,
    sku text,
    category text,
    category_2 text,
    brand text,
    unit text NOT NULL DEFAULT 'pieza',
    costo_unitario numeric(14,2) NOT NULL DEFAULT 0,
    moneda text NOT NULL DEFAULT 'MXN',
    active boolean NOT NULL DEFAULT true,
    is_key_product boolean NOT NULL DEFAULT false,
    min_stock numeric(14,4) NOT NULL DEFAULT 0,
    erp_tags jsonb NOT NULL DEFAULT '{}',
    metadata jsonb NOT NULL DEFAULT '{}',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz
);

CREATE TABLE IF NOT EXISTS drenafort_proy001.erp_folio_sequences (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    folio text UNIQUE NOT NULL,
    empresa_id text NOT NULL DEFAULT 'EMP_DRENAFORT',
    project_code text NOT NULL DEFAULT 'PROY-001',
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

CREATE OR REPLACE FUNCTION drenafort_proy001.reserve_erp_folio(
    p_scope text,
    p_prefix text,
    p_digits integer DEFAULT 5,
    p_empresa_id text DEFAULT 'EMP_DRENAFORT',
    p_project_code text DEFAULT 'PROY-001',
    p_module_code text DEFAULT 'inventario',
    p_min_current integer DEFAULT 0
)
RETURNS text
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = drenafort_proy001, public
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

    INSERT INTO drenafort_proy001.erp_folio_sequences (
        folio, empresa_id, project_code, module_code, scope, prefix, current_number, digits
    )
    VALUES (
        'SEQ-' || upper(regexp_replace(coalesce(p_module_code, 'erp'), '[^A-Za-z0-9]+', '_', 'g')) || '-' || v_scope || '-' || v_prefix,
        p_empresa_id, p_project_code, p_module_code, v_scope, v_prefix, p_min_current, p_digits
    )
    ON CONFLICT (empresa_id, project_code, module_code, scope, prefix) DO NOTHING;

    UPDATE drenafort_proy001.erp_folio_sequences
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

CREATE INDEX IF NOT EXISTS idx_erp_products_key ON drenafort_proy001.erp_products (empresa_id, product_key);
CREATE INDEX IF NOT EXISTS idx_erp_products_sku ON drenafort_proy001.erp_products (empresa_id, sku);

GRANT USAGE ON SCHEMA drenafort_proy001 TO anon, authenticated, service_role;
GRANT ALL ON ALL TABLES IN SCHEMA drenafort_proy001 TO anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA drenafort_proy001
  GRANT ALL ON TABLES TO anon, authenticated, service_role;
