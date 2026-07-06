"""Upsert de CFDIs en conta4all.cfdi_documentos por managed_rfc_id (plataforma pública)."""
from __future__ import annotations

import json
import os
import urllib.request
import urllib.error


_DDL_SETUP = """
CREATE SCHEMA IF NOT EXISTS conta4all;

CREATE TABLE IF NOT EXISTS conta4all.managed_rfcs (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_user_id uuid NOT NULL,
  company_id    text,
  rfc           text NOT NULL,
  label         text DEFAULT '',
  created_at    timestamptz DEFAULT now(),
  UNIQUE (owner_user_id, rfc)
);

ALTER TABLE conta4all.managed_rfcs ADD COLUMN IF NOT EXISTS company_id text;
CREATE INDEX IF NOT EXISTS managed_rfcs_company_idx ON conta4all.managed_rfcs (company_id);

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
ALTER TABLE conta4all.cfdi_documentos ADD COLUMN IF NOT EXISTS conceptos        jsonb DEFAULT '[]'::jsonb;
ALTER TABLE conta4all.cfdi_documentos ADD COLUMN IF NOT EXISTS impuestos        jsonb DEFAULT '{}'::jsonb;
ALTER TABLE conta4all.cfdi_documentos ADD COLUMN IF NOT EXISTS iva              numeric(18,2) DEFAULT 0;
ALTER TABLE conta4all.cfdi_documentos ADD COLUMN IF NOT EXISTS xml_raw          text;
ALTER TABLE conta4all.cfdi_documentos ADD COLUMN IF NOT EXISTS has_xml          boolean DEFAULT false;
ALTER TABLE conta4all.cfdi_documentos ADD COLUMN IF NOT EXISTS pdf_url          text DEFAULT '';
UPDATE conta4all.cfdi_documentos SET has_xml = (NULLIF(xml_raw, '') IS NOT NULL);

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
ALTER TABLE conta4all.managed_rfcs ENABLE ROW LEVEL SECURITY;

GRANT USAGE ON SCHEMA conta4all TO service_role;
GRANT ALL ON ALL TABLES IN SCHEMA conta4all TO service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA conta4all GRANT ALL ON TABLES TO service_role;
"""


class Conta4allCfdiStoreService:

    def ejecutar(self, context: dict) -> dict:
        if context.get("action") == "setup_table":
            return self._setup(context)
        if context.get("action") == "backfill_xml_fields":
            return self._backfill_xml_fields(context)

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
                "conceptos":        c.get("conceptos", []),
                "impuestos":        c.get("impuestos", {}),
                "iva":              float(c.get("iva") or 0),
                "xml_raw":          c.get("xml_raw", ""),
                "has_xml":          bool(c.get("xml_raw")),
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

    def _backfill_xml_fields(self, context: dict) -> dict:
        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run - backfill no ejecutado", "data": {"actualizados": 0}}

        url = (context.get("platform_supabase_url") or
               os.getenv("PLATFORM_SUPABASE_URL", "")).rstrip("/")
        key = (context.get("platform_supabase_service_role_key") or
               os.getenv("PLATFORM_SUPABASE_SERVICE_ROLE_KEY", ""))
        if not url or not key:
            return {"ok": False, "error": "Faltan PLATFORM_SUPABASE_URL o PLATFORM_SUPABASE_SERVICE_ROLE_KEY"}

        managed_rfc_id = str(context.get("managed_rfc_id") or "").strip()
        limit = int(context.get("limit", 1000))
        filters = ["select=managed_rfc_id,uuid_cfdi,xml_raw", "xml_raw=not.is.null", f"limit={limit}"]
        if managed_rfc_id:
            filters.append(f"managed_rfc_id=eq.{managed_rfc_id}")
        endpoint = f"{url}/rest/v1/cfdi_documentos?{'&'.join(filters)}"
        req = urllib.request.Request(endpoint, headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Accept-Profile": "conta4all",
            "User-Agent": "FactoryFactory/0.1 (+https://github.com/)",
        })
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                rows = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            return {"ok": False, "error": f"Supabase HTTP {e.code}: {body[:300]}"}

        updates = []
        for row in rows:
            derived = self._derive_xml_fields(row.get("xml_raw") or "")
            if not derived:
                continue
            updates.append({
                "managed_rfc_id": row.get("managed_rfc_id"),
                "uuid_cfdi": row.get("uuid_cfdi"),
                **derived,
            })

        if not updates:
            return {"ok": True, "message": "Sin XMLs parseables para backfill", "data": {"actualizados": 0}}

        updated = 0
        for item in updates:
            payload = {
                "conceptos": item["conceptos"],
                "impuestos": item["impuestos"],
                "iva": item["iva"],
            }
            endpoint = (
                f"{url}/rest/v1/cfdi_documentos?"
                f"managed_rfc_id=eq.{item['managed_rfc_id']}&uuid_cfdi=eq.{item['uuid_cfdi']}"
            )
            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "apikey": key,
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                    "Content-Profile": "conta4all",
                    "Prefer": "return=minimal",
                    "User-Agent": "FactoryFactory/0.1 (+https://github.com/)",
                },
                method="PATCH",
            )
            try:
                with urllib.request.urlopen(req, timeout=20) as resp:
                    resp.read()
                updated += 1
            except urllib.error.HTTPError:
                continue

        return {"ok": True, "message": f"{updated} CFDIs recalculados desde XML",
                "data": {"actualizados": updated, "revisados": len(rows)}}

    def _derive_xml_fields(self, xml_raw: str) -> dict:
        if not xml_raw:
            return {}
        try:
            import xml.etree.ElementTree as ET
            if isinstance(xml_raw, str):
                xml_text = xml_raw.lstrip("\ufeff")
                root = ET.fromstring(xml_text)
            else:
                root = ET.fromstring(xml_raw)
        except Exception:
            return {}
        ns = root.tag[1:].split("}", 1)[0] if root.tag.startswith("{") else "http://www.sat.gob.mx/cfd/4"

        conceptos = []
        for c in root.findall(f".//{{{ns}}}Concepto"):
            conceptos.append({
                "descripcion": c.get("Descripcion", ""),
                "cantidad": c.get("Cantidad", ""),
                "valor_unitario": c.get("ValorUnitario", ""),
                "importe": c.get("Importe", ""),
                "clave_prod_serv": c.get("ClaveProdServ", ""),
            })

        impuestos = {
            "iva_trasladado": 0.0,
            "iva_retenido": 0.0,
            "isr_retenido": 0.0,
            "total_trasladados": 0.0,
            "total_retenidos": 0.0,
        }
        for traslado in root.findall(f".//{{{ns}}}Traslado"):
            importe = self._to_float(traslado.get("Importe", "0"))
            impuestos["total_trasladados"] += importe
            if traslado.get("Impuesto") == "002":
                impuestos["iva_trasladado"] += importe
        for retencion in root.findall(f".//{{{ns}}}Retencion"):
            importe = self._to_float(retencion.get("Importe", "0"))
            impuestos["total_retenidos"] += importe
            if retencion.get("Impuesto") == "002":
                impuestos["iva_retenido"] += importe
            if retencion.get("Impuesto") == "001":
                impuestos["isr_retenido"] += importe
        return {
            "conceptos": conceptos,
            "impuestos": impuestos,
            "iva": round(impuestos["iva_trasladado"] - impuestos["iva_retenido"], 2),
        }

    def _to_float(self, value: str) -> float:
        try:
            return float(value or 0)
        except Exception:
            return 0.0
