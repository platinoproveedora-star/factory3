"""Upsert de CFDIs parseados en Supabase tabla cfdi_documentos (dedup por empresa_id+uuid_cfdi)."""
from __future__ import annotations

import json
import os
import urllib.request


_DDL = """
CREATE SCHEMA IF NOT EXISTS {schema};

CREATE TABLE IF NOT EXISTS {schema}.cfdi_documentos (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  empresa_id       text NOT NULL,
  uuid_cfdi        text NOT NULL,
  tipo             text NOT NULL DEFAULT 'E',
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
  rfc_propietario  text,
  created_at       timestamptz DEFAULT now(),
  UNIQUE (empresa_id, uuid_cfdi)
);

GRANT USAGE ON SCHEMA {schema} TO anon, authenticated, service_role;
GRANT ALL ON ALL TABLES IN SCHEMA {schema} TO anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA {schema}
  GRANT ALL ON TABLES TO anon, authenticated, service_role;
"""


class SatCfdiStoreService:

    def ejecutar(self, context: dict) -> dict:
        schema          = context.get("schema") or os.getenv("SUPABASE_SCHEMA", "uc102_proy001")

        if context.get("action") == "setup":
            return self._setup(schema, context)

        cfdis           = context.get("cfdis") or []
        empresa_id      = context.get("empresa_id") or os.getenv("EMPRESA_ID", "")
        rfc_propietario = context.get("rfc_propietario") or os.getenv("SAT_RFC", "")
        tipo            = context.get("tipo", "E")

        if context.get("dry_run"):
            return {"ok": True, "message": "dry_run", "data": {"insertados": 0, "total": len(cfdis)}}

        if not empresa_id:
            return {"ok": False, "error": "Falta empresa_id (o env EMPRESA_ID)"}

        if not cfdis:
            return {"ok": True, "message": "0 CFDIs — nada que guardar", "data": {"insertados": 0}}

        url  = os.getenv("SUPABASE_URL", "").rstrip("/")
        key  = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        if not url or not key:
            return {"ok": False, "error": "Faltan SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY"}

        rows = []
        for c in cfdis:
            if not c.get("uuid"):
                continue
            rows.append({
                "empresa_id":      empresa_id,
                "uuid_cfdi":       c["uuid"],
                "tipo":            tipo,
                "rfc_emisor":      c.get("rfc_emisor", ""),
                "nombre_emisor":   c.get("nombre_emisor", ""),
                "rfc_receptor":    c.get("rfc_receptor", ""),
                "nombre_receptor": c.get("nombre_receptor", ""),
                "fecha_emision":   (c.get("fecha_emision") or "")[:10] or None,
                "fecha_timbrado":  c.get("fecha_timbrado") or None,
                "total":           float(c.get("total") or 0),
                "subtotal":        float(c.get("subtotal") or 0),
                "descuento":       float(c.get("descuento") or 0),
                "moneda":          c.get("moneda", "MXN"),
                "tipo_comprobante": c.get("tipo_comprobante", ""),
                "metodo_pago":     c.get("metodo_pago", ""),
                "forma_pago":      c.get("forma_pago", ""),
                "uso_cfdi":        c.get("uso_cfdi", ""),
                "conceptos":       json.dumps(c.get("conceptos", []), ensure_ascii=False),
                "xml_raw":         c.get("xml_raw", ""),
                "rfc_propietario": rfc_propietario,
            })

        if not rows:
            return {"ok": True, "message": "Sin UUIDs válidos", "data": {"insertados": 0}}

        import urllib.error
        endpoint = f"{url}/rest/v1/cfdi_documentos"
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(rows).encode("utf-8"),
            headers={
                "apikey":          key,
                "Authorization":   f"Bearer {key}",
                "Content-Type":    "application/json",
                "Content-Profile": schema,
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
            "message": f"{len(rows)} CFDIs guardados en Supabase",
            "data":    {"insertados": len(rows), "total": len(cfdis)},
        }

    def _setup(self, schema: str, context: dict) -> dict:
        """Crea tabla cfdi_documentos y aplica GRANTs via Management API."""
        sql = _DDL.format(schema=schema)

        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run — SQL que se ejecutaría:", "data": {"sql": sql}}

        access_token = (context.get("supabase_access_token") or
                        os.getenv("SUPABASE_ACCESS_TOKEN", "")).strip()
        project_ref  = (context.get("supabase_project_ref") or
                        os.getenv("SUPABASE_PROJECT_REF", "")).strip()

        if not project_ref:
            url = os.getenv("SUPABASE_URL", "")
            import re
            m = re.search(r"https://([^.]+)\.supabase\.co", url)
            project_ref = m.group(1) if m else ""

        if not access_token or not project_ref:
            return {
                "ok":    False,
                "error": "Faltan SUPABASE_ACCESS_TOKEN y/o SUPABASE_PROJECT_REF para ejecutar setup",
                "data":  {"sql_manual": sql},
            }

        import urllib.error
        endpoint = f"https://api.supabase.com/v1/projects/{project_ref}/database/query"
        req = urllib.request.Request(
            endpoint,
            data=json.dumps({"query": sql}).encode("utf-8"),
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
            return {"ok": True, "message": f"Setup completado para schema {schema}"}
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            return {"ok": False, "error": f"Management API {e.code}: {body[:300]}",
                    "data": {"sql_manual": sql}}
