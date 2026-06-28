"""Upsert de CFDIs en conta4all.cfdi_documentos por managed_rfc_id (plataforma pública)."""
from __future__ import annotations

import json
import os
import urllib.request
import urllib.error


_DDL_SETUP = """
CREATE SCHEMA IF NOT EXISTS conta4all;

CREATE TABLE IF NOT EXISTS conta4all.cfdi_documentos (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  managed_rfc_id uuid NOT NULL,
  uuid_cfdi      text NOT NULL,
  created_at     timestamptz DEFAULT now(),
  UNIQUE (managed_rfc_id, uuid_cfdi)
);

ALTER TABLE conta4all.cfdi_documentos ADD COLUMN IF NOT EXISTS tipo             text;
ALTER TABLE conta4all.cfdi_documentos ADD COLUMN IF NOT EXISTS rfc_emisor       text;
ALTER TABLE conta4all.cfdi_documentos ADD COLUMN IF NOT EXISTS nombre_emisor    text;
ALTER TABLE conta4all.cfdi_documentos ADD COLUMN IF NOT EXISTS rfc_receptor     text;
ALTER TABLE conta4all.cfdi_documentos ADD COLUMN IF NOT EXISTS nombre_receptor  text;
ALTER TABLE conta4all.cfdi_documentos ADD COLUMN IF NOT EXISTS fecha_emision    date;
ALTER TABLE conta4all.cfdi_documentos ADD COLUMN IF NOT EXISTS fecha_timbrado   timestamptz;
ALTER TABLE conta4all.cfdi_documentos ADD COLUMN IF NOT EXISTS total            numeric(18,2) DEFAULT 0;
ALTER TABLE conta4all.cfdi_documentos ADD COLUMN IF NOT EXISTS subtotal         numeric(18,2) DEFAULT 0;
ALTER TABLE conta4all.cfdi_documentos ADD COLUMN IF NOT EXISTS descuento        numeric(18,2) DEFAULT 0;
ALTER TABLE conta4all.cfdi_documentos ADD COLUMN IF NOT EXISTS moneda           text DEFAULT 'MXN';
ALTER TABLE conta4all.cfdi_documentos ADD COLUMN IF NOT EXISTS tipo_comprobante text;
ALTER TABLE conta4all.cfdi_documentos ADD COLUMN IF NOT EXISTS metodo_pago      text;
ALTER TABLE conta4all.cfdi_documentos ADD COLUMN IF NOT EXISTS forma_pago       text;
ALTER TABLE conta4all.cfdi_documentos ADD COLUMN IF NOT EXISTS uso_cfdi         text;
ALTER TABLE conta4all.cfdi_documentos ADD COLUMN IF NOT EXISTS xml_raw          text;

CREATE TABLE IF NOT EXISTS conta4all.sat_solicitudes (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  managed_rfc_id  uuid,
  rfc             text NOT NULL,
  id_solicitud    text NOT NULL UNIQUE,
  tipo            text NOT NULL DEFAULT 'E',
  tipo_solicitud  text NOT NULL DEFAULT 'CFDI',
  tipo_comprobante text DEFAULT '',
  rfc_contraparte text DEFAULT '',
  fecha_inicio    date NOT NULL,
  fecha_fin       date NOT NULL,
  estado          int DEFAULT 1,
  paquetes        jsonb DEFAULT '[]'::jsonb,
  num_cfdis       int DEFAULT 0,
  ultimo_error    text DEFAULT '',
  created_at      timestamptz DEFAULT now(),
  updated_at      timestamptz DEFAULT now()
);

ALTER TABLE conta4all.sat_solicitudes ADD COLUMN IF NOT EXISTS tipo_comprobante text DEFAULT '';
ALTER TABLE conta4all.sat_solicitudes ADD COLUMN IF NOT EXISTS rfc_contraparte text DEFAULT '';
ALTER TABLE conta4all.sat_solicitudes ADD COLUMN IF NOT EXISTS ultimo_error text DEFAULT '';

CREATE INDEX IF NOT EXISTS sat_solicitudes_lookup_idx
  ON conta4all.sat_solicitudes (managed_rfc_id, rfc, tipo, tipo_solicitud, fecha_inicio, fecha_fin, estado);

ALTER TABLE conta4all.cfdi_documentos ENABLE ROW LEVEL SECURITY;
ALTER TABLE conta4all.sat_solicitudes ENABLE ROW LEVEL SECURITY;

GRANT USAGE ON SCHEMA conta4all TO service_role;
GRANT ALL ON ALL TABLES IN SCHEMA conta4all TO service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA conta4all GRANT ALL ON TABLES TO service_role;
"""


class Conta4allCfdiStoreService:

    def ejecutar(self, context: dict) -> dict:
        if context.get("action") == "setup_table":
            return self._setup(context)

        managed_rfc_id = str(context.get("managed_rfc_id") or "").strip()
        cfdis          = context.get("cfdis") or []
        tipo           = context.get("tipo", "E")

        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run", "data": {"insertados": 0, "total": len(cfdis)}}

        if not managed_rfc_id:
            return {"ok": False, "error": "managed_rfc_id requerido en context"}

        if not cfdis:
            return {"ok": True, "message": "0 CFDIs — nada que guardar", "data": {"insertados": 0}}

        url = (context.get("platform_supabase_url") or
               os.getenv("PLATFORM_SUPABASE_URL", "")).rstrip("/")
        key = (context.get("platform_supabase_service_role_key") or
               os.getenv("PLATFORM_SUPABASE_SERVICE_ROLE_KEY", ""))
        if not url or not key:
            return {"ok": False, "error": "Faltan PLATFORM_SUPABASE_URL o PLATFORM_SUPABASE_SERVICE_ROLE_KEY"}

        rows = []
        for c in cfdis:
            if not c.get("uuid"):
                continue
            rows.append({
                "managed_rfc_id":   managed_rfc_id,
                "uuid_cfdi":        c["uuid"],
                "tipo":             tipo,
                "rfc_emisor":       c.get("rfc_emisor", ""),
                "nombre_emisor":    c.get("nombre_emisor", ""),
                "rfc_receptor":     c.get("rfc_receptor", ""),
                "nombre_receptor":  c.get("nombre_receptor", ""),
                "fecha_emision":    (c.get("fecha_emision") or "")[:10] or None,
                "fecha_timbrado":   c.get("fecha_timbrado") or None,
                "total":            float(c.get("total") or 0),
                "subtotal":         float(c.get("subtotal") or 0),
                "descuento":        float(c.get("descuento") or 0),
                "moneda":           c.get("moneda", "MXN"),
                "tipo_comprobante": c.get("tipo_comprobante", ""),
                "metodo_pago":      c.get("metodo_pago", ""),
                "forma_pago":       c.get("forma_pago", ""),
                "uso_cfdi":         c.get("uso_cfdi", ""),
                "xml_raw":          c.get("xml_raw", ""),
            })

        if not rows:
            return {"ok": True, "message": "Sin UUIDs válidos", "data": {"insertados": 0}}

        endpoint = f"{url}/rest/v1/cfdi_documentos?on_conflict=managed_rfc_id,uuid_cfdi"
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(rows).encode("utf-8"),
            headers={
                "apikey":          key,
                "Authorization":   f"Bearer {key}",
                "Content-Type":    "application/json",
                "Content-Profile": "conta4all",
                "Prefer":          "resolution=merge-duplicates,return=minimal",
                "User-Agent":      "FactoryFactory/0.1 (+https://github.com/)",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                resp.read()
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            return {"ok": False, "error": f"Supabase HTTP {e.code}: {body[:300]}"}

        return {
            "ok":      True,
            "message": f"{len(rows)} CFDIs guardados en conta4all",
            "data":    {"insertados": len(rows), "total": len(cfdis)},
        }

    def _setup(self, context: dict) -> dict:
        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run — DDL no ejecutado", "data": {"sql": _DDL_SETUP}}

        access_token = (context.get("platform_supabase_access_token") or
                        os.getenv("PLATFORM_SUPABASE_ACCESS_TOKEN", "")).strip()
        project_ref  = (context.get("platform_supabase_project_ref") or
                        os.getenv("PLATFORM_SUPABASE_PROJECT_REF", "")).strip()

        if not project_ref:
            import re
            url = context.get("platform_supabase_url") or os.getenv("PLATFORM_SUPABASE_URL", "")
            m = re.search(r"https://([^.]+)\.supabase\.co", url)
            project_ref = m.group(1) if m else ""

        if not access_token or not project_ref:
            return {
                "ok":   False,
                "error": "Faltan PLATFORM_SUPABASE_ACCESS_TOKEN y/o PLATFORM_SUPABASE_PROJECT_REF",
                "data": {"sql_manual": _DDL_SETUP},
            }

        endpoint = f"https://api.supabase.com/v1/projects/{project_ref}/database/query"
        req = urllib.request.Request(
            endpoint,
            data=json.dumps({"query": _DDL_SETUP}).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type":  "application/json",
                "User-Agent":    "FactoryFactory/0.1 (+https://github.com/)",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                resp.read()
            return {"ok": True, "message": "Setup conta4all.cfdi_documentos completado"}
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            return {"ok": False, "error": f"Management API {e.code}: {body[:300]}",
                    "data": {"sql_manual": _DDL_SETUP}}
