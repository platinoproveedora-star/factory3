-- ============================================================
-- ERP Migration: PROY-001_GASTOS — EMP_DURALON
-- Ejecutar en: Supabase SQL Editor → proyecto ddcwdtqiupwtyltdpakm
-- Seguro: usa IF NOT EXISTS / IF NOT EXISTS — no rompe datos existentes
-- ============================================================

-- USUARIOS: identidad ERP + campos globales
ALTER TABLE uc101_proy001.usuarios
  ADD COLUMN IF NOT EXISTS empresa_id      text     NOT NULL DEFAULT 'EMP_DURALON',
  ADD COLUMN IF NOT EXISTS project_code    text     NOT NULL DEFAULT 'PROY-001',
  ADD COLUMN IF NOT EXISTS module_code     text     NOT NULL DEFAULT 'gastos',
  ADD COLUMN IF NOT EXISTS global_user_id  uuid     NULL,
  ADD COLUMN IF NOT EXISTS phone           text     NULL,
  ADD COLUMN IF NOT EXISTS email           text     NULL,
  ADD COLUMN IF NOT EXISTS modules_allowed text[]   NOT NULL DEFAULT ARRAY['gastos'];

-- CATEGORIAS_GASTO: identidad ERP
ALTER TABLE uc101_proy001.categorias_gasto
  ADD COLUMN IF NOT EXISTS empresa_id   text NOT NULL DEFAULT 'EMP_DURALON',
  ADD COLUMN IF NOT EXISTS project_code text NOT NULL DEFAULT 'PROY-001',
  ADD COLUMN IF NOT EXISTS module_code  text NOT NULL DEFAULT 'gastos';

-- GASTOS: identidad ERP + campos ERP de conexión con otros módulos
ALTER TABLE uc101_proy001.gastos
  ADD COLUMN IF NOT EXISTS empresa_id        text  NOT NULL DEFAULT 'EMP_DURALON',
  ADD COLUMN IF NOT EXISTS project_code      text  NOT NULL DEFAULT 'PROY-001',
  ADD COLUMN IF NOT EXISTS module_code       text  NOT NULL DEFAULT 'gastos',
  ADD COLUMN IF NOT EXISTS cost_center_id    uuid  NULL,
  ADD COLUMN IF NOT EXISTS customer_id       uuid  NULL,
  ADD COLUMN IF NOT EXISTS supplier_id       uuid  NULL,
  ADD COLUMN IF NOT EXISTS sales_order_id    uuid  NULL,
  ADD COLUMN IF NOT EXISTS purchase_order_id uuid  NULL,
  ADD COLUMN IF NOT EXISTS asset_id          uuid  NULL,
  ADD COLUMN IF NOT EXISTS cta_retiro_id     uuid  NULL,
  ADD COLUMN IF NOT EXISTS cta_retiro_folio  text  NULL,
  ADD COLUMN IF NOT EXISTS cta_retiro_nombre text  NULL,
  ADD COLUMN IF NOT EXISTS erp_tags          jsonb NOT NULL DEFAULT '{}';

CREATE INDEX IF NOT EXISTS gastos_cta_retiro_id_idx
  ON uc101_proy001.gastos (cta_retiro_id);

-- GASTO_DOCUMENTOS: identidad ERP
ALTER TABLE uc101_proy001.gasto_documentos
  ADD COLUMN IF NOT EXISTS empresa_id   text NOT NULL DEFAULT 'EMP_DURALON',
  ADD COLUMN IF NOT EXISTS project_code text NOT NULL DEFAULT 'PROY-001',
  ADD COLUMN IF NOT EXISTS module_code  text NOT NULL DEFAULT 'gastos';

-- GASTO_EVENTOS: identidad ERP
ALTER TABLE uc101_proy001.gasto_eventos
  ADD COLUMN IF NOT EXISTS empresa_id   text NOT NULL DEFAULT 'EMP_DURALON',
  ADD COLUMN IF NOT EXISTS project_code text NOT NULL DEFAULT 'PROY-001',
  ADD COLUMN IF NOT EXISTS module_code  text NOT NULL DEFAULT 'gastos';
