"""Lista y filtra CFDIs de conta4all.cfdi_documentos por managed_rfc_id (kind=data, dashboard público)."""
from __future__ import annotations

import os
import json
import urllib.request
import urllib.error


class Conta4allCfdiListService:

    def ejecutar(self, context: dict) -> dict:
        if context.get("dry_run"):
            return {"ok": True, "message": "dry_run", "data": {"cfdis": [], "total": 0}}

        url = (context.get("platform_supabase_url") or
               os.getenv("PLATFORM_SUPABASE_URL", "")).rstrip("/")
        key = (context.get("platform_supabase_service_role_key") or
               os.getenv("PLATFORM_SUPABASE_SERVICE_ROLE_KEY", ""))
        if not url or not key:
            return {"ok": False, "error": "Faltan PLATFORM_SUPABASE_URL o PLATFORM_SUPABASE_SERVICE_ROLE_KEY"}

        managed_rfc_id = str(context.get("managed_rfc_id") or "").strip()
        tipo           = (context.get("tipo") or "").strip()
        fecha_inicio   = (context.get("fecha_inicio") or "").strip()
        fecha_fin      = (context.get("fecha_fin") or "").strip()
        mes            = (context.get("mes") or "").strip()
        limit          = int(context.get("limit", 1000))

        if not managed_rfc_id:
            return {"ok": False, "error": "managed_rfc_id requerido"}

        filters = [f"managed_rfc_id=eq.{managed_rfc_id}"]
        if tipo:
            filters.append(f"tipo=eq.{tipo}")
        if fecha_inicio:
            filters.append(f"fecha_emision=gte.{fecha_inicio}")
        if fecha_fin:
            filters.append(f"fecha_emision=lte.{fecha_fin}")
        elif mes:
            try:
                y, m_str = mes.split("-")
                m_int = int(m_str)
                next_y = int(y) + (m_int // 12)
                next_m = m_int % 12 + 1
                filters.append(f"fecha_emision=gte.{mes}-01")
                filters.append(f"fecha_emision=lt.{next_y}-{next_m:02d}-01")
            except Exception:
                pass

        cols = ("uuid_cfdi,tipo,rfc_emisor,nombre_emisor,rfc_receptor,nombre_receptor,"
                "fecha_emision,fecha_timbrado,total,subtotal,descuento,moneda,"
                "tipo_comprobante,metodo_pago,forma_pago,uso_cfdi,created_at")

        qs       = "&".join(filters + [f"limit={limit}", "order=fecha_emision.desc"])
        endpoint = f"{url}/rest/v1/cfdi_documentos?select={cols}&{qs}"

        req = urllib.request.Request(
            endpoint,
            headers={
                "apikey":         key,
                "Authorization":  f"Bearer {key}",
                "Accept-Profile": "conta4all",
                "User-Agent":     "FactoryFactory/0.1 (+https://github.com/)",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                cfdis = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            return {"ok": False, "error": f"Supabase {e.code}: {body[:200]}"}

        monto     = sum(float(c.get("total") or 0) for c in cfdis)
        total_e   = sum(1 for c in cfdis if c.get("tipo") == "E")
        total_r   = sum(1 for c in cfdis if c.get("tipo") == "R")

        return {
            "ok":      True,
            "message": f"{len(cfdis)} CFDIs",
            "data": {
                "cfdis":            cfdis,
                "total":            len(cfdis),
                "total_emitidos":   total_e,
                "total_recibidos":  total_r,
                "monto_total":      round(monto, 2),
            },
        }
