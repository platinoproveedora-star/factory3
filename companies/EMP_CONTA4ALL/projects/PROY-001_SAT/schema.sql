-- PROY-001 SAT CFDI Sync — EMP_CONTA4ALL
-- Schema: uc102_proy001
-- Ejecutar en: Supabase → SQL Editor

-- Paso 1: Crear schema (si no existe)
CREATE SCHEMA IF NOT EXISTS uc102_proy001;

-- Paso 2: Tabla principal de CFDIs
-- Ver docs/TABLES.md sección "Schema uc102_proy001" para la spec completa.

CREATE TABLE IF NOT EXISTS uc102_proy001.cfdi_documentos (
  id               uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  empresa_id       text        NOT NULL,
  rfc_propietario  text        NOT NULL,
  uuid_cfdi        text        NOT NULL,
  tipo             text        NOT NULL CHECK (tipo IN ('E', 'R')),
  rfc_emisor       text,
  nombre_emisor    text,
  rfc_receptor     text,
  nombre_receptor  text,
  fecha_emision    date,
  fecha_timbrado   timestamptz,
  total            numeric,
  subtotal         numeric,
  descuento        numeric     DEFAULT 0,
  moneda           text        DEFAULT 'MXN',
  tipo_comprobante text,
  metodo_pago      text,
  forma_pago       text,
  uso_cfdi         text,
  estado           text        DEFAULT 'vigente',
  conceptos        jsonb,
  xml_raw          text,
  created_at       timestamptz DEFAULT now(),
  UNIQUE (empresa_id, uuid_cfdi)
);

-- Índices recomendados
CREATE INDEX IF NOT EXISTS idx_cfdi_uc102_empresa
  ON uc102_proy001.cfdi_documentos (empresa_id);

CREATE INDEX IF NOT EXISTS idx_cfdi_uc102_rfc_prop
  ON uc102_proy001.cfdi_documentos (rfc_propietario);

CREATE INDEX IF NOT EXISTS idx_cfdi_uc102_tipo
  ON uc102_proy001.cfdi_documentos (tipo);

CREATE INDEX IF NOT EXISTS idx_cfdi_uc102_fecha
  ON uc102_proy001.cfdi_documentos (fecha_emision);

CREATE INDEX IF NOT EXISTS idx_cfdi_uc102_rfc_emisor
  ON uc102_proy001.cfdi_documentos (rfc_emisor);

CREATE INDEX IF NOT EXISTS idx_cfdi_uc102_rfc_receptor
  ON uc102_proy001.cfdi_documentos (rfc_receptor);

-- Paso 3: Exponer schema en Supabase Data API
-- Dashboard → Settings → Data API → Exposed schemas → agregar uc102_proy001
