"""Logística Platino — DB + business logic."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime
from pathlib import Path

_AI_DIR = Path(__file__).parent.parent / "factory" / "skills" / "internos" / "ai_interpreter"
if str(_AI_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_DIR))
import service as _ai  # noqa: E402

_URL       = os.getenv("SUPABASE_URL", "").rstrip("/")
_KEY       = (
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    or os.getenv("SUPABASE_SERVICE_KEY")
    or os.getenv("SUPABASE_ANON_KEY")
    or ""
)
_SCHEMA    = "logplat"
_BOT_TOKEN = os.getenv("FACTORY3_ADMIN_BOT_TOKEN", "")


def _headers(write: bool = False) -> dict:
    h = {
        "apikey":        _KEY,
        "Authorization": f"Bearer {_KEY}",
        "Content-Type":  "application/json",
    }
    h["Content-Profile" if write else "Accept-Profile"] = _SCHEMA
    if write:
        h["Prefer"] = "return=representation"
    return h


def _rest_url(table: str, params: dict | None = None) -> str:
    base = f"{_URL}/rest/v1/{table}"
    return f"{base}?{urllib.parse.urlencode(params)}" if params else base


def _req(method: str, table: str, payload=None, params: dict | None = None, write: bool = False) -> dict:
    url  = _rest_url(table, params)
    body = json.dumps(payload).encode() if payload is not None else None
    req  = urllib.request.Request(url, data=body, method=method, headers=_headers(write=write))
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode()
            return {"ok": True, "data": json.loads(raw) if raw else []}
    except urllib.error.HTTPError as e:
        return {"ok": False, "error": f"HTTP {e.code}: {e.read().decode()}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _next_folio(table: str, prefix: str) -> str:
    r = _req("GET", table, params={"select": "folio", "order": "folio.desc", "limit": "1"})
    if r.get("ok") and r.get("data"):
        last = r["data"][0].get("folio", "")
        if last and "-" in last:
            try:
                n = int(last.split("-")[1]) + 1
                return f"{prefix}-{n:03d}"
            except (ValueError, IndexError):
                pass
    return f"{prefix}-001"


# ─── VIAJES ──────────────────────────────────────────────────────────────────

def crear_viaje(data: dict) -> dict:
    folio = _next_folio("viajes", "VIA")
    now   = datetime.utcnow().isoformat()
    costo = float(data.get("costo_viaje") or 0)
    venta = float(data.get("precio_venta_viaje") or 0)
    row   = {
        "folio":              folio,
        "empresa_id":         data.get("empresa_id", "LOGPLAT"),
        "cliente":            data.get("cliente") or "",
        "origen":             data.get("origen") or "",
        "destino":            data.get("destino") or "",
        "fecha_salida":       data.get("fecha_salida") or None,
        "fecha_llegada":      data.get("fecha_llegada") or None,
        "costo_viaje":        costo,
        "precio_venta_viaje": venta,
        "utilidad_viaje":     venta - costo,
        "chofer":             data.get("chofer") or "",
        "estatus_viaje":      "activo",
        "estatus_pago":       data.get("estatus_pago") or "por_cobrar",
        "created_at":         now,
        "updated_at":         now,
    }
    r = _req("POST", "viajes", row, write=True)
    if r.get("ok"):
        viaje = (r["data"][0] if isinstance(r.get("data"), list) else r.get("data")) or {}
        if row["estatus_pago"] == "por_cobrar":
            _crear_cxc(viaje)
    return r


def _crear_cxc(viaje: dict) -> None:
    folio = _next_folio("cuentas_por_cobrar", "CXC")
    now   = datetime.utcnow().isoformat()
    monto = float(viaje.get("precio_venta_viaje") or 0)
    _req("POST", "cuentas_por_cobrar", {
        "folio":           folio,
        "empresa_id":      viaje.get("empresa_id", "LOGPLAT"),
        "numero_viaje":    viaje.get("folio"),
        "cliente":         viaje.get("cliente"),
        "monto_total":     monto,
        "monto_pagado":    0,
        "saldo_pendiente": monto,
        "fecha_viaje":     viaje.get("fecha_salida"),
        "estatus_cobro":   "pendiente",
        "created_at":      now,
        "updated_at":      now,
    }, write=True)


# ─── GASTOS ──────────────────────────────────────────────────────────────────

def crear_gasto(data: dict) -> dict:
    folio = _next_folio("gastos", "GAS")
    now   = datetime.utcnow().isoformat()
    row   = {
        "folio":         folio,
        "empresa_id":    data.get("empresa_id", "LOGPLAT"),
        "numero_viaje":  data.get("numero_viaje") or None,
        "fecha_gasto":   data.get("fecha_gasto") or date.today().isoformat(),
        "fecha_captura": now,
        "monto_gasto":   float(data.get("monto_gasto") or 0),
        "concepto":      data.get("concepto") or "",
        "chofer":        data.get("chofer") or "",
        "tipo_gasto":    data.get("tipo_gasto") or "otro",
        "created_at":    now,
        "updated_at":    now,
    }
    r = _req("POST", "gastos", row, write=True)
    if r.get("ok") and data.get("numero_viaje"):
        _recalcular_utilidad(data["numero_viaje"])
    return r


def _recalcular_utilidad(numero_viaje: str) -> None:
    rg = _req("GET", "gastos", params={"numero_viaje": f"eq.{numero_viaje}", "select": "monto_gasto"})
    if not rg.get("ok"):
        return
    total_gastos = sum(float(g.get("monto_gasto", 0)) for g in rg.get("data", []))
    rv = _req("GET", "viajes", params={"folio": f"eq.{numero_viaje}", "select": "precio_venta_viaje,costo_viaje"})
    if not rv.get("ok") or not rv.get("data"):
        return
    v        = rv["data"][0]
    utilidad = float(v.get("precio_venta_viaje", 0)) - float(v.get("costo_viaje", 0)) - total_gastos
    _req("PATCH", "viajes",
         {"utilidad_viaje": utilidad, "updated_at": datetime.utcnow().isoformat()},
         params={"folio": f"eq.{numero_viaje}"}, write=True)


# ─── PAGOS ───────────────────────────────────────────────────────────────────

def crear_pago(data: dict) -> dict:
    folio = _next_folio("pagos", "PAG")
    now   = datetime.utcnow().isoformat()
    row   = {
        "folio":         folio,
        "empresa_id":    data.get("empresa_id", "LOGPLAT"),
        "numero_viaje":  data.get("numero_viaje") or None,
        "cliente":       data.get("cliente") or "",
        "fecha_pago":    data.get("fecha_pago") or date.today().isoformat(),
        "monto_pago":    float(data.get("monto_pago") or 0),
        "metodo_pago":   data.get("metodo_pago") or "transferencia",
        "observaciones": data.get("observaciones") or "",
        "created_at":    now,
        "updated_at":    now,
    }
    r = _req("POST", "pagos", row, write=True)
    if r.get("ok") and data.get("numero_viaje"):
        _actualizar_cxc(data["numero_viaje"], float(data.get("monto_pago") or 0))
    return r


def _actualizar_cxc(numero_viaje: str, monto_pago: float) -> None:
    r = _req("GET", "cuentas_por_cobrar", params={"numero_viaje": f"eq.{numero_viaje}", "select": "*"})
    if not r.get("ok") or not r.get("data"):
        return
    cxc          = r["data"][0]
    nuevo_pagado = float(cxc.get("monto_pagado", 0)) + monto_pago
    saldo        = max(0.0, float(cxc.get("monto_total", 0)) - nuevo_pagado)
    estatus      = "pagado" if saldo <= 0 else ("parcial" if nuevo_pagado > 0 else "pendiente")
    now          = datetime.utcnow().isoformat()
    _req("PATCH", "cuentas_por_cobrar",
         {"monto_pagado": nuevo_pagado, "saldo_pendiente": saldo, "estatus_cobro": estatus, "updated_at": now},
         params={"numero_viaje": f"eq.{numero_viaje}"}, write=True)
    _req("PATCH", "viajes",
         {"estatus_pago": estatus, "updated_at": now},
         params={"folio": f"eq.{numero_viaje}"}, write=True)


# ─── IA — wrappers sobre ai_interpreter ──────────────────────────────────────

_ACTIONS = {
    "viaje": {"cliente": None, "origen": None, "destino": None, "fecha_salida": None,
               "fecha_llegada": None, "chofer": None, "costo_viaje": None,
               "precio_venta_viaje": None, "estatus_pago": "por_cobrar"},
    "gasto": {"concepto": None, "monto_gasto": None, "fecha_gasto": None,
               "chofer": None, "numero_viaje": None, "tipo_gasto": None},
    "pago":  {"monto_pago": None, "fecha_pago": None, "metodo_pago": None,
               "numero_viaje": None, "cliente": None},
}


def interpretar_libre(texto: str, content_b64: str | None, media_type: str | None, hint: str = "") -> dict:
    r = _ai.run({
        "mode":        "classify",
        "actions":     _ACTIONS,
        "text":        texto or "",
        "content_b64": content_b64 or "",
        "media_type":  media_type or "text/plain",
        "hint":        hint,
        "context":     "Eres un asistente de captura logística para Platino Logística.",
    })
    if not r.get("ok"):
        return r
    d = r.get("data", {})
    return {"ok": True, "action": d.get("action", "desconocido"), "data": d.get("fields", {})}


# ─── REPORTES ─────────────────────────────────────────────────────────────────

def reporte_viajes(limit: int = 10) -> list[dict]:
    r = _req("GET", "viajes", params={
        "select": "folio,cliente,origen,destino,fecha_salida,precio_venta_viaje,utilidad_viaje,estatus_pago",
        "order": "created_at.desc", "limit": str(limit),
    })
    return r.get("data", []) if r.get("ok") else []


def reporte_gastos(limit: int = 10) -> list[dict]:
    r = _req("GET", "gastos", params={
        "select": "folio,fecha_gasto,concepto,monto_gasto,chofer,numero_viaje",
        "order": "created_at.desc", "limit": str(limit),
    })
    return r.get("data", []) if r.get("ok") else []


def lista_pagos(limit: int = 10) -> list[dict]:
    r = _req("GET", "pagos", params={
        "select": "folio,cliente,numero_viaje,fecha_pago,monto_pago,metodo_pago",
        "order": "created_at.desc", "limit": str(limit),
    })
    return r.get("data", []) if r.get("ok") else []


# ─── TELEGRAM FILE DOWNLOAD ──────────────────────────────────────────────────

def descargar_telegram(file_id: str) -> tuple[bytes | None, str | None]:
    if not _BOT_TOKEN:
        return None, "FACTORY3_ADMIN_BOT_TOKEN no configurado"
    try:
        with urllib.request.urlopen(
            f"https://api.telegram.org/bot{_BOT_TOKEN}/getFile?file_id={file_id}", timeout=10
        ) as r:
            data = json.loads(r.read())
        if not data.get("ok"):
            return None, "getFile falló"
        file_path = data["result"]["file_path"]
        with urllib.request.urlopen(
            f"https://api.telegram.org/file/bot{_BOT_TOKEN}/{file_path}", timeout=30
        ) as r:
            return r.read(), None
    except Exception as e:
        return None, str(e)
