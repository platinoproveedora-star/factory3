"""Upsert de CFDIs parseados en Supabase tabla cfdi_documentos (dedup por uuid_cfdi)."""
from __future__ import annotations

import json
import os
import urllib.request


class SatCfdiStoreService:

    def ejecutar(self, context: dict) -> dict:
        cfdis          = context.get("cfdis") or []
        rfc_propietario = context.get("rfc_propietario") or os.getenv("SAT_RFC", "")
        tipo            = context.get("tipo", "E")

        if context.get("dry_run"):
            return {"ok": True, "message": "dry_run", "data": {"insertados": 0, "total": len(cfdis)}}

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

        endpoint = f"{url}/rest/v1/cfdi_documentos"
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(rows).encode("utf-8"),
            headers={
                "apikey":          key,
                "Authorization":   f"Bearer {key}",
                "Content-Type":    "application/json",
                "Prefer":          "resolution=merge-duplicates,return=minimal",
                "User-Agent":      "FactoryFactory/0.1 (+https://github.com/)",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp.read()

        return {
            "ok":      True,
            "message": f"{len(rows)} CFDIs guardados en Supabase",
            "data":    {"insertados": len(rows), "total": len(cfdis)},
        }
