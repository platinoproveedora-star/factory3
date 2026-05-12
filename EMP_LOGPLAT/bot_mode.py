"""Handler for /logplat mode.

Comandos: /gasto  /pago  /viaje
  - Texto libre sin hint  → chat con Haiku sobre los datos
  - /gasto + texto        → interpreta y guarda gasto
  - /gasto + foto         → extrae gasto de imagen + sube comprobante
  - /pago  + texto        → interpreta y guarda pago
  - /pago  + foto         → extrae pago de imagen + sube comprobante
  - /viaje + texto        → interpreta y guarda viaje
  - /viaje + foto/PDF     → sube documento, pregunta número de viaje
  - Siguiente msg tras /viaje+foto → folio → liga doc al viaje
"""

from __future__ import annotations

import base64
import sys
from pathlib import Path

_DIR = Path(__file__).parent
if str(_DIR) not in sys.path:
    sys.path.insert(0, str(_DIR))

import service as svc

_AYUDA = (
    "<b>Modo LOGPLAT activo</b> — Logística Platino\n\n"
    "<b>Capturar:</b>\n"
    "/gasto   — registrar gasto (texto o foto del comprobante)\n"
    "/pago    — registrar pago (texto o foto del recibo)\n"
    "/viaje   — registrar viaje o subir documento a un viaje\n\n"
    "<b>Consultar:</b>\n"
    "/reporteviajes — últimos 10 viajes\n"
    "/reportegastos — últimos 10 gastos\n"
    "/pagos         — últimos 10 pagos\n"
    "o escribe cualquier pregunta.\n\n"
    "/ayuda — esta ayuda | /salir — salir del modo"
)

_PROMPTS = {
    "gasto": "💸 Envía los datos del gasto (texto) o una foto del comprobante.",
    "pago":  "💰 Envía los datos del pago (texto) o una foto del recibo.",
    "viaje": "🚚 Envía texto con los datos del viaje, o una foto/PDF para subirlo como documento.",
}


def _normalizar_folio(texto: str) -> str:
    """'22', '022', 'via-22', 'viaje 22' → 'VIA-022'"""
    import re
    t = texto.upper().strip()
    if not t:
        return ""
    m = re.search(r"\d+", t)
    if not m:
        return t
    return f"VIA-{int(m.group()):03d}"


def ejecutar(update: dict, state: dict) -> dict:
    message  = update.get("message", {})
    raw_text = (message.get("text") or "").strip()
    text     = raw_text.lower()
    photo    = message.get("photo")
    document = message.get("document")

    # ── Comandos fijos ────────────────────────────────────────────────────────
    if text in ("/ayuda", "/help"):
        return _ok(_AYUDA, state)
    if text == "/reporteviajes":
        return _reporte_viajes(state)
    if text == "/reportegastos":
        return _reporte_gastos(state)
    if text == "/pagos":
        return _lista_pagos(state)

    # ── Activar captura ───────────────────────────────────────────────────────
    if text in ("/gasto", "/viaje", "/pago"):
        hint = text[1:]
        return _ok(_PROMPTS[hint], {**state, "hint": hint})

    hint      = state.get("hint", "")
    new_state = {k: v for k, v in state.items() if k != "hint"}

    # ── Esperando folio para ligar doc de viaje ───────────────────────────────
    if hint == "viaje_doc_pending":
        doc_url  = state.get("doc_url", "")
        doc_name = state.get("doc_name", "")
        folio    = _normalizar_folio(raw_text)
        if not folio:
            return _ok("Escribe el número de viaje (ej: VIA-022 o solo 22).", state)
        clean = {k: v for k, v in state.items() if k not in ("hint", "doc_url", "doc_name")}
        if svc.agregar_doc_viaje(folio, doc_url, nombre=doc_name):
            return _ok(f"✅ Documento guardado en viaje <b>{folio}</b>.\nPuedes enviar otro archivo para el mismo viaje.", clean)
        return _ok(f"No pude guardar el documento en {folio}. Verifica el número e intenta de nuevo.", state)

    # ── Con hint activo ───────────────────────────────────────────────────────
    if hint in ("gasto", "pago", "viaje"):
        if photo or document:
            return _capture_doc(photo, document, hint, new_state)
        if raw_text:
            return _capture_text(raw_text, hint, new_state)

    # ── Sin hint ──────────────────────────────────────────────────────────────
    if photo or document:
        return _ok("Usa /gasto, /pago o /viaje antes de enviar un archivo.", state)
    if raw_text:
        return _chat_libre(raw_text, state)

    return _ok("Escribe algo o usa /ayuda para ver comandos.", state)


# ─── CAPTURA ─────────────────────────────────────────────────────────────────

def _capture_text(text: str, hint: str, state: dict) -> dict:
    r = svc.interpretar_libre(text, None, None, hint)
    if not r.get("ok"):
        return _ok(f"No pude interpretar: {r.get('error')}", state)
    return _dispatch(hint, r.get("data", {}), state)


def _capture_doc(photo, document, hint: str, state: dict) -> dict:
    if photo:
        file_id    = photo[-1]["file_id"]
        filename   = f"{photo[-1]['file_id']}.jpg"
        media_type = "image/jpeg"
    else:
        file_id    = document["file_id"]
        filename   = document.get("file_name") or f"{document['file_id']}.pdf"
        media_type = document.get("mime_type", "application/pdf")

    file_bytes, err = svc.descargar_telegram(file_id)
    if err:
        return _ok(f"Error descargando archivo: {err}", state)

    # Subir a Storage
    doc_url, err_up = svc.subir_documento(file_bytes, filename, media_type)

    # Viaje + foto: solo subir doc y pedir folio
    if hint == "viaje":
        if not doc_url:
            return _ok(f"Error subiendo documento: {err_up}", state)
        new_state = {**state, "hint": "viaje_doc_pending", "doc_url": doc_url, "doc_name": filename}
        return _ok("📎 Documento subido.\n¿A qué número de viaje lo ligo? (ej: VIA-022 o solo 22)", new_state)

    # Gasto / Pago: extraer datos + guardar con id_doc
    r = svc.interpretar_libre("", base64.b64encode(file_bytes).decode(), media_type, hint)
    if not r.get("ok"):
        return _ok(f"No pude leer el documento: {r.get('error')}", state)
    data = r.get("data", {})
    if doc_url:
        data["id_doc"] = doc_url
    return _dispatch(hint, data, state)


# ─── DISPATCH ────────────────────────────────────────────────────────────────

def _dispatch(action: str, data: dict, state: dict) -> dict:
    if action == "viaje": return _save_viaje(data, state)
    if action == "gasto": return _save_gasto(data, state)
    if action == "pago":  return _save_pago(data, state)
    return _ok("No pude determinar el tipo. Usa /gasto, /pago o /viaje.", state)


# ─── SAVERS ──────────────────────────────────────────────────────────────────

def _save_viaje(data: dict, state: dict) -> dict:
    r = svc.crear_viaje(data)
    if not r.get("ok"):
        return _ok(f"Error guardando viaje: {r.get('error')}", state)
    v   = (r["data"][0] if isinstance(r.get("data"), list) else r.get("data")) or {}
    msg = (f"✅ Viaje <b>{v.get('folio','?')}</b> registrado.\n"
           f"Ruta: {data.get('origen') or '?'} → {data.get('destino') or '?'}\n"
           f"Cliente: {data.get('cliente') or '—'}")
    return _ok(msg, state)


def _save_gasto(data: dict, state: dict) -> dict:
    r = svc.crear_gasto(data)
    if not r.get("ok"):
        return _ok(f"Error guardando gasto: {r.get('error')}", state)
    g   = (r["data"][0] if isinstance(r.get("data"), list) else r.get("data")) or {}
    msg = (f"✅ Gasto <b>{g.get('folio','?')}</b> registrado.\n"
           f"Concepto: {data.get('concepto') or '—'}\n"
           f"Monto: ${float(data.get('monto_gasto') or 0):,.0f}\n"
           f"Viaje: {data.get('numero_viaje') or '— (asigna desde el dash)'}")
    if data.get("id_doc"):
        msg += "\n📎 Comprobante guardado."
    return _ok(msg, state)


def _save_pago(data: dict, state: dict) -> dict:
    r = svc.crear_pago(data)
    if not r.get("ok"):
        return _ok(f"Error guardando pago: {r.get('error')}", state)
    p   = (r["data"][0] if isinstance(r.get("data"), list) else r.get("data")) or {}
    msg = (f"✅ Pago <b>{p.get('folio','?')}</b> registrado.\n"
           f"Monto: ${float(data.get('monto_pago') or 0):,.0f}\n"
           f"Método: {data.get('metodo_pago') or '—'}\n"
           f"Viaje: {data.get('numero_viaje') or '— (asigna desde el dash)'}")
    if data.get("id_doc"):
        msg += "\n📎 Comprobante guardado."
    return _ok(msg, state)


# ─── CHAT LIBRE ──────────────────────────────────────────────────────────────

def _chat_libre(texto: str, state: dict) -> dict:
    r = svc.consultar(texto)
    if not r.get("ok"):
        return _ok(f"Error consultando: {r.get('error')}", state)
    return _ok(r["response"], state)


# ─── REPORTES ────────────────────────────────────────────────────────────────

def _reporte_viajes(state: dict) -> dict:
    viajes = svc.reporte_viajes(10)
    if not viajes:
        return _ok("Sin viajes registrados.", state)
    lines = ["<b>Últimos viajes:</b>"]
    for v in viajes:
        lines.append(
            f"\n<b>{v.get('folio')}</b> — {v.get('cliente') or '—'}\n"
            f"  → {v.get('destino') or '—'}\n"
            f"  Venta: ${float(v.get('precio_venta_viaje') or 0):,.0f} | {v.get('estatus_pago')}"
        )
    return _ok("\n".join(lines), state)


def _reporte_gastos(state: dict) -> dict:
    gastos = svc.reporte_gastos(10)
    if not gastos:
        return _ok("Sin gastos registrados.", state)
    lines = ["<b>Últimos gastos:</b>"]
    for g in gastos:
        lines.append(
            f"\n<b>{g.get('folio')}</b> — {g.get('concepto') or '—'}\n"
            f"  ${float(g.get('monto_gasto') or 0):,.0f} | {g.get('fecha_gasto')} | "
            f"Viaje: {g.get('numero_viaje') or 'ninguno'}"
        )
    return _ok("\n".join(lines), state)


def _lista_pagos(state: dict) -> dict:
    pagos = svc.lista_pagos(10)
    if not pagos:
        return _ok("Sin pagos registrados.", state)
    lines = ["<b>Últimos pagos:</b>"]
    for p in pagos:
        lines.append(
            f"\n<b>{p.get('folio')}</b>\n"
            f"  ${float(p.get('monto_pago') or 0):,.0f} | {p.get('fecha_pago')} | "
            f"{p.get('metodo_pago')} | Viaje: {p.get('numero_viaje') or 'ninguno'}"
        )
    return _ok("\n".join(lines), state)


# ─── HELPERS ─────────────────────────────────────────────────────────────────

def _ok(response: str, state: dict, markup: dict | None = None) -> dict:
    r: dict = {"response": response, "state": state}
    if markup:
        r["reply_markup"] = markup
    return r
