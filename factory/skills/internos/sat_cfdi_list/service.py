"""Lista y filtra CFDIs de Supabase para el dashboard (kind=data)."""
from __future__ import annotations

import os
import urllib.request
import json


class SatCfdiListService:

    def ejecutar(self, context: dict) -> dict:
        if context.get("dry_run"):
            return {"ok": True, "message": "dry_run", "data": {"cfdis": [], "total": 0}}

        url = os.getenv("SUPABASE_URL", "").rstrip("/")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        if not url or not key:
            return {"ok": False, "error": "Faltan SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY"}

        tipo            = context.get("tipo", "")           # E / R / ""
        rfc_propietario = context.get("rfc_propietario") or os.getenv("SAT_RFC", "")
        mes             = context.get("mes", "")             # YYYY-MM
        dia             = context.get("dia", "")             # YYYY-MM-DD
        limit           = int(context.get("limit", 500))

        filters = []
        if tipo:
            filters.append(f"tipo=eq.{tipo}")
        if rfc_propietario:
            filters.append(f"rfc_propietario=eq.{rfc_propietario}")
        if dia:
            filters.append(f"fecha_emision=eq.{dia}")
        elif mes:
            filters.append(f"fecha_emision=gte.{mes}-01")
            y, m = mes.split("-")
            next_m = f"{int(y) + (int(m) // 12)}-{int(m) % 12 + 1:02d}"
            filters.append(f"fecha_emision=lt.{next_m}-01")

        qs = "&".join(filters + [f"limit={limit}", "order=fecha_emision.desc"])
        endpoint = f"{url}/rest/v1/cfdi_documentos?select=uuid_cfdi,tipo,rfc_emisor,nombre_emisor,rfc_receptor,nombre_receptor,fecha_emision,total,moneda,tipo_comprobante,forma_pago,metodo_pago,rfc_propietario,estado&{qs}"

        req = urllib.request.Request(
            endpoint,
            headers={
                "apikey":        key,
                "Authorization": f"Bearer {key}",
                "User-Agent":    "FactoryFactory/0.1 (+https://github.com/)",
            },
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            cfdis = json.loads(resp.read().decode("utf-8"))

        total_i = sum(1 for c in cfdis if c.get("tipo") == "I")
        total_e = sum(1 for c in cfdis if c.get("tipo") == "E")
        monto   = sum(float(c.get("total") or 0) for c in cfdis)

        return {
            "ok":      True,
            "message": f"{len(cfdis)} CFDIs",
            "data": {
                "cfdis":          cfdis,
                "total":          len(cfdis),
                "total_ingresos": total_i,
                "total_egresos":  total_e,
                "monto_total":    round(monto, 2),
                "filtros":        {"tipo": tipo, "mes": mes, "dia": dia, "rfc": rfc_propietario},
            },
        }
