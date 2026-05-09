"""KPI aggregation for Logística Platino dashboard."""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from datetime import date, timedelta

_URL    = os.getenv("SUPABASE_URL", "").rstrip("/")
_KEY    = (
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    or os.getenv("SUPABASE_SERVICE_KEY")
    or os.getenv("SUPABASE_ANON_KEY")
    or ""
)
_SCHEMA = "logplat"


def _headers() -> dict:
    return {
        "apikey":         _KEY,
        "Authorization":  f"Bearer {_KEY}",
        "Accept-Profile": _SCHEMA,
    }


def _get(table: str, params: dict) -> list:
    url = f"{_URL}/rest/v1/{table}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode()) or []
    except Exception:
        return []


class EmpLogplatKpisService:

    def ejecutar(self, _context: dict) -> dict:
        hoy     = date.today()
        sem_ini = hoy - timedelta(days=hoy.weekday())
        mes_ini = hoy.replace(day=1)

        viajes = _get("viajes", {"select": "utilidad_viaje,precio_venta_viaje,costo_viaje,fecha_salida,estatus_pago"})
        gastos = _get("gastos",  {"select": "monto_gasto,fecha_gasto"})
        cxc    = _get("cuentas_por_cobrar", {"select": "saldo_pendiente,estatus_cobro,fecha_vencimiento"})

        def _d(s):
            return date.fromisoformat(s[:10]) if s else hoy

        viajes_sem    = [v for v in viajes if _d(v.get("fecha_salida")) >= sem_ini]
        gastos_sem    = [g for g in gastos  if _d(g.get("fecha_gasto"))  >= sem_ini]
        ingresos_sem  = sum(float(v.get("precio_venta_viaje") or 0) for v in viajes_sem)
        gastos_sem_t  = sum(float(g.get("monto_gasto") or 0) for g in gastos_sem)
        utilidad_sem  = sum(float(v.get("utilidad_viaje") or 0) for v in viajes_sem)
        saldo_pend    = sum(float(c.get("saldo_pendiente") or 0) for c in cxc if c.get("estatus_cobro") != "pagado")
        cxc_vencidas  = sum(
            1 for c in cxc
            if c.get("estatus_cobro") == "pendiente" and c.get("fecha_vencimiento") and _d(c["fecha_vencimiento"]) < hoy
        )

        return {
            "ok": True,
            "data": {
                "semana": {
                    "ingresos": round(ingresos_sem, 2),
                    "gastos":   round(gastos_sem_t, 2),
                    "utilidad": round(utilidad_sem, 2),
                    "viajes":   len(viajes_sem),
                },
                "cxc": {
                    "saldo_pendiente": round(saldo_pend, 2),
                    "cxc_vencidas":    cxc_vencidas,
                },
                "total": {
                    "viajes":     len(viajes),
                    "por_cobrar": sum(1 for v in viajes if v.get("estatus_pago") == "por_cobrar"),
                },
                "fecha": hoy.isoformat(),
            },
        }
