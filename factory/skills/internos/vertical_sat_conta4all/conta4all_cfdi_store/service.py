"""Upsert de CFDIs en conta4all.cfdi_documentos por managed_rfc_id (plataforma pública)."""
from __future__ import annotations

import json
import os
import urllib.request
import urllib.error


_DDL_SETUP = """
CREATE SCHEMA IF NOT EXISTS conta4all;

CREATE TABLE IF NOT EXISTS conta4all.cfdi_documentos (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  managed_rfc_id   uuid NOT NULL,
  uuid_cfdi        text NOT NULL,
  tipo             text CHECK (tipo IN ('E','R')),
  rfc_emisor       text,
  nombre_emisor    text,
  rfc_receptor     text,
  nombre_receptor  text,
  fecha_emision    date,
  fecha_timbrado   timestamptz,
  total            numeric(18,2) DEFAULT 0,
  subtotal         numeric(18,2) DEFAULT 0,
  descuento        numeric(18,2) DEFAULT 0,
  moneda           text DEFAULT 'MXN',
  tipo_comprobante text,
  metodo_pago      text,
  forma_pago       text,
  uso_cfdi         text,
  conceptos        jsonb DEFAULT '[]'::jsonb,
  xml_raw          text,
  created_at       timestamptz DEFAULT now(),
  UNIQUE (managed_rfc_id, uuid_cfdi)
);

ALTER TABLE conta4all.cfdi_documentos ENABLE ROW LEVEL SECURITY;

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
                "conceptos":        json.dumps(c.get("conceptos", []), ensure_ascii=False),
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
