"""Logística Platino — DB + business logic."""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime

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


# ─── IA / EXTRACCIÓN ─────────────────────────────────────────────────────────

def extraer_documento(content_b64: str, media_type: str, schema: dict, context: str = "") -> dict:
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return {"ok": False, "error": "ANTHROPIC_API_KEY no configurada"}

    schema_str  = json.dumps(schema, ensure_ascii=False, indent=2)
    instruction = (
        (f"{context}\n\n" if context else "") +
        f"Extrae los datos del documento y devuelve SOLO un JSON con exactamente estos campos:\n{schema_str}\n"
        "Si un campo no se puede determinar usa null. No incluyas texto fuera del JSON."
    )

    if media_type == "text/plain":
        text     = base64.b64decode(content_b64).decode("utf-8", errors="replace")
        messages = [{"role": "user", "content": f"{instruction}\n\nTexto:\n{text}"}]
    elif media_type == "application/pdf":
        messages = [{"role": "user", "content": [
            {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": content_b64}},
            {"type": "text", "text": instruction},
        ]}]
    else:
        messages = [{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": content_b64}},
            {"type": "text", "text": instruction},
        ]}]

    payload = {"model": "claude-haiku-4-5-20251001", "max_tokens": 1024, "messages": messages}
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(payload).encode(),
        headers={
            "content-type":      "application/json",
            "x-api-key":         api_key,
            "anthropic-version": "2023-06-01",
            "anthropic-beta":    "pdfs-2024-09-25",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode())
        text  = "".join(
            item.get("text", "") for item in result.get("content", []) if item.get("type") == "text"
        ).strip()
        start = text.find("{")
        end   = text.rfind("}") + 1
        if start >= 0 and end > start:
            return {"ok": True, "extracted": json.loads(text[start:end])}
        return {"ok": False, "error": "Sin JSON en respuesta", "raw": text}
    except Exception as e:
        return {"ok": False, "error": str(e)}


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
