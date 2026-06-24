-- Logística Platino — Schema y tablas
-- Actualizado: 2026-05-11
-- 1. Ejecutar este SQL en Supabase SQL Editor
-- 2. Dashboard > Settings > API > Exposed schemas > agregar "logplat"

CREATE SCHEMA IF NOT EXISTS logplat;

CREATE TABLE IF NOT EXISTS logplat.viajes (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    folio               text UNIQUE NOT NULL,
    empresa_id          text NOT NULL DEFAULT 'LOGPLAT',
    cliente             text,
    origen              text,
    destino             text,
    fecha_salida        date,
    fecha_llegada       date,
    costo_viaje         numeric(12,2) DEFAULT 0,
    precio_venta_viaje  numeric(12,2) DEFAULT 0,
    utilidad_viaje      numeric(12,2) DEFAULT 0,
    chofer              text,
    estatus_viaje       text DEFAULT 'activo',
    estatus_pago        text DEFAULT 'por_cobrar',
    id_doc              text,
    created_at          timestamptz DEFAULT now(),
    updated_at          timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS logplat.gastos (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    folio         text UNIQUE NOT NULL,
    empresa_id    text NOT NULL DEFAULT 'LOGPLAT',
    numero_viaje  text,
    fecha_gasto   date,
    fecha_captura timestamptz DEFAULT now(),
    monto_gasto   numeric(12,2) DEFAULT 0,
    concepto      text,
    chofer        text,
    tipo_gasto    text,
    id_doc        text,
    created_at    timestamptz DEFAULT now(),
    updated_at    timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS logplat.pagos (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    folio         text UNIQUE NOT NULL,
    empresa_id    text NOT NULL DEFAULT 'LOGPLAT',
    numero_viaje  text,
    cliente       text,
    fecha_pago    date,
    monto_pago    numeric(12,2) DEFAULT 0,
    metodo_pago   text DEFAULT 'transferencia',
    observaciones text,
    id_doc        text,
    created_at    timestamptz DEFAULT now(),
    updated_at    timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS logplat.cuentas_por_cobrar (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    folio             text UNIQUE NOT NULL,
    empresa_id        text NOT NULL DEFAULT 'LOGPLAT',
    numero_viaje      text,
    cliente           text,
    monto_total       numeric(12,2) DEFAULT 0,
    monto_pagado      numeric(12,2) DEFAULT 0,
    saldo_pendiente   numeric(12,2) DEFAULT 0,
    fecha_viaje       date,
    fecha_vencimiento date,
    estatus_cobro     text DEFAULT 'pendiente',
    created_at        timestamptz DEFAULT now(),
    updated_at        timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS logplat.viaje_docs (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    folio       text UNIQUE NOT NULL,
    viaje_folio text NOT NULL,
    doc_url     text NOT NULL,
    tipo        text NOT NULL DEFAULT 'otro',
    nombre      text,
    created_at  timestamptz DEFAULT now()
);

-- PASO FINAL OBLIGATORIO: exponer schema en Data API (PostgREST)
-- NO ejecutar este ALTER manualmente — sobrescribiría otros schemas expuestos.
-- Usar el skill:
--   supabase_expose_schema  { "schema": "logplat", "dry_run": false }
-- El skill hace append seguro sin tocar schemas existentes.
