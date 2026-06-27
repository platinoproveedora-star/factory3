"""Lista y filtra CFDIs de Supabase para el dashboard (kind=data)."""
from __future__ import annotations

import os
import urllib.request
import urllib.error
import json


class SatCfdiListService:

    def ejecutar(self, context: dict) -> dict:
        if context.get("dry_run"):
            return {"ok": True, "message": "dry_run", "data": {"cfdis": [], "total": 0}}

        url    = os.getenv("SUPABASE_URL", "").rstrip("/")
        key    = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        schema = context.get("schema") or os.getenv("SUPABASE_SCHEMA", "uc102_proy001")
        if not url or not key:
            return {"ok": False, "error": "Faltan SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY"}

        empresa_id      = context.get("empresa_id") or os.getenv("EMPRESA_ID", "")
        tipo            = context.get("tipo", "")            # E / R / ""
        rfc_propietario = context.get("rfc_propietario") or os.getenv("SAT_RFC", "")
        fecha_inicio    = (context.get("fecha_inicio") or "").strip()
        fecha_fin       = (context.get("fecha_fin") or "").strip()
        mes             = (context.get("mes") or "").strip()   # YYYY-MM fallback
        dia             = (context.get("dia") or "").strip()   # YYYY-MM-DD fallback
        limit           = int(context.get("limit", 1000))

        filters = []
        if empresa_id:
            filters.append(f"empresa_id=eq.{empresa_id}")
        if tipo:
            filters.append(f"tipo=eq.{tipo}")
        if rfc_propietario:
            filters.append(f"rfc_propietario=eq.{rfc_propietario}")

        # Rango de fechas: fecha_inicio/fecha_fin tienen prioridad sobre mes/dia
        if fecha_inicio:
            filters.append(f"fecha_emision=gte.{fecha_inicio}")
        if fecha_fin:
            filters.append(f"fecha_emision=lte.{fecha_fin}")
        elif not fecha_inicio:
            if dia:
                filters.append(f"fecha_emision=eq.{dia}")
            elif mes:
                try:
                    y, m = mes.split("-")
                    next_m = f"{int(y) + (int(m) // 12)}-{int(m) % 12 + 1:02d}"
                    filters.append(f"fecha_emision=gte.{mes}-01")
                    filters.append(f"fecha_emision=lt.{next_m}-01")
                except Exception:
                    pass

        cols = ("uuid_cfdi,tipo,rfc_emisor,nombre_emisor,rfc_receptor,nombre_receptor,"
                "fecha_emision,fecha_timbrado,total,subtotal,descuento,moneda,"
                "tipo_comprobante,metodo_pago,forma_pago,uso_cfdi,rfc_propietario,created_at")

        qs       = "&".join(filters + [f"limit={limit}", "order=fecha_emision.desc"])
        endpoint = f"{url}/rest/v1/cfdi_documentos?select={cols}&{qs}"

        req = urllib.request.Request(
            endpoint,
            headers={
                "apikey":         key,
                "Authorization":  f"Bearer {key}",
                "Accept-Profile": schema,
                "User-Agent":     "FactoryFactory/0.1 (+https://github.com/)",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                cfdis = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            return {"ok": False, "error": f"Supabase {e.code}: {body[:200]}"}

        monto = sum(float(c.get("total") or 0) for c in cfdis)
        total_i = sum(1 for c in cfdis if (c.get("tipo_comprobante") or "").upper() == "I")
        total_e = sum(1 for c in cfdis if (c.get("tipo_comprobante") or "").upper() == "E")

        return {
            "ok":      True,
            "message": f"{len(cfdis)} CFDIs",
            "data": {
                "cfdis":          cfdis,
                "total":          len(cfdis),
                "total_ingresos": total_i,
                "total_egresos":  total_e,
                "monto_total":    round(monto, 2),
            },
        }
