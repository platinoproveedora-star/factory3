"""Handler for /logplat mode — viajes, gastos, pagos."""

from __future__ import annotations

import base64
import sys
from pathlib import Path

_DIR = Path(__file__).parent
if str(_DIR) not in sys.path:
    sys.path.insert(0, str(_DIR))

import service as svc  # noqa: E402

_AYUDA = (
    "<b>Modo LOGPLAT activo</b> — Logística Platino\n\n"
    "/+viaje — registrar viaje\n"
    "/+gasto — registrar gasto\n"
    "/+pago  — registrar pago\n"
    "/ayuda  — esta ayuda\n"
    "/salir  — salir del modo"
)

_VIAJE_SCHEMA = {
    "cliente": None, "origen": None, "destino": None,
    "fecha_salida": None, "fecha_llegada": None,
    "chofer": None, "costo_viaje": None,
    "precio_venta_viaje": None, "estatus_pago": "por_cobrar",
}
_GASTO_SCHEMA = {
    "concepto": None, "monto_gasto": None, "fecha_gasto": None,
    "chofer": None, "numero_viaje": None, "tipo_gasto": None,
}
_PAGO_SCHEMA = {
    "monto_pago": None, "fecha_pago": None,
    "metodo_pago": None, "numero_viaje": None, "cliente": None,
}

_VIAJE_STEPS = [
    ("cliente",            "¿Cliente?"),
    ("origen",             "¿Origen?"),
    ("destino",            "¿Destino?"),
    ("fecha_salida",       "¿Fecha salida? (YYYY-MM-DD)"),
    ("fecha_llegada",      "¿Fecha llegada? (YYYY-MM-DD)"),
    ("costo_viaje",        "¿Costo del viaje? (MXN)"),
    ("precio_venta_viaje", "¿Precio de venta? (MXN)"),
    ("chofer",             "¿Chofer?"),
    ("estatus_pago",       "¿Estatus pago?\npor_cobrar / pagado / parcial"),
]
_GASTO_STEPS = [
    ("numero_viaje", "¿Número de viaje? (VIA-001 o escribe 'ninguno')"),
    ("concepto",     "¿Concepto? (diesel / casetas / comida / reparación / maniobra / otro)"),
    ("monto_gasto",  "¿Monto? (MXN)"),
    ("chofer",       "¿Chofer?"),
    ("fecha_gasto",  "¿Fecha? (YYYY-MM-DD o 'hoy')"),
]
_PAGO_STEPS = [
    ("numero_viaje", "¿Número de viaje? (VIA-001)"),
    ("monto_pago",   "¿Monto del pago? (MXN)"),
    ("metodo_pago",  "¿Método?\ntransferencia / efectivo / cheque"),
    ("fecha_pago",   "¿Fecha del pago? (YYYY-MM-DD o 'hoy')"),
]


def ejecutar(update: dict, state: dict) -> dict:
    message  = update.get("message", {})
    raw_text = (message.get("text") or "").strip()
    text     = raw_text.lower()
    photo    = message.get("photo")
    document = message.get("document")
    wizard   = state.get("wizard", {})

    if text in ("/ayuda", "/help"):
        return _ok(_AYUDA, state)

    if raw_text == "/+viaje":
        return _ok("¿Captura manual o tienes imagen/PDF del documento?",
                   {**state, "wizard": {"action": "viaje", "step": "tipo", "data": {}}},
                   _tipo_markup())

    if raw_text == "/+gasto":
        return _ok("¿Captura manual o tienes imagen/PDF del ticket?",
                   {**state, "wizard": {"action": "gasto", "step": "tipo", "data": {}}},
                   _tipo_markup())

    if raw_text == "/+pago":
        return _ok("¿Captura manual o tienes comprobante de pago?",
                   {**state, "wizard": {"action": "pago", "step": "tipo", "data": {}}},
                   _tipo_markup())

    if wizard:
        return _wizard(text, photo, document, wizard, state)

    return _ok("Escribe /ayuda para ver los comandos.", state)


# ─── WIZARD ──────────────────────────────────────────────────────────────────

def _wizard(text: str, photo, document, wizard: dict, state: dict) -> dict:
    action = wizard.get("action")
    step   = wizard.get("step")

    if step == "tipo":
        if photo or document or text == "imagen":
            if photo or document:
                return _handle_doc(photo, document, wizard, state)
            return _ok("Envía la foto o PDF ahora.",
                       {**state, "wizard": {**wizard, "step": "esperando_doc"}})
        if text in ("manual", "/manual"):
            steps = {"viaje": _VIAJE_STEPS, "gasto": _GASTO_STEPS, "pago": _PAGO_STEPS}[action]
            return _ok(steps[0][1], {**state, "wizard": {**wizard, "step": steps[0][0]}})
        return _ok("Elige Manual o Imagen/PDF.", state, _tipo_markup())

    if step == "esperando_doc":
        if photo or document:
            return _handle_doc(photo, document, wizard, state)
        return _ok("Envía la foto o PDF.", {**state, "wizard": wizard})

    if action == "viaje":
        return _advance(_VIAJE_STEPS, text, wizard, state, _save_viaje)
    if action == "gasto":
        return _advance(_GASTO_STEPS, text, wizard, state, _save_gasto)
    if action == "pago":
        return _advance(_PAGO_STEPS, text, wizard, state, _save_pago)

    return _ok("No entendí. Escribe /ayuda.", {**state, "wizard": {}})


# ─── STEP ADVANCER ───────────────────────────────────────────────────────────

def _advance(steps: list, text: str, wizard: dict, state: dict, save_fn) -> dict:
    step = wizard.get("step")
    data = dict(wizard.get("data", {}))
    keys = [s[0] for s in steps]
    idx  = keys.index(step) if step in keys else -1

    if idx < 0:
        return _ok("Algo salió mal. Empieza de nuevo con /+viaje, /+gasto o /+pago.",
                   {**state, "wizard": {}})

    val = "" if text in ("ninguno",) else text
    if step in ("fecha_salida", "fecha_llegada", "fecha_gasto", "fecha_pago") and text == "hoy":
        from datetime import date as _d
        val = _d.today().isoformat()
    data[step] = val

    if idx + 1 < len(steps):
        nk, np = steps[idx + 1]
        return _ok(np, {**state, "wizard": {**wizard, "step": nk, "data": data}})

    return save_fn(data, state)


# ─── SAVERS ──────────────────────────────────────────────────────────────────

def _save_viaje(data: dict, state: dict) -> dict:
    r = svc.crear_viaje(data)
    if not r.get("ok"):
        return _ok(f"Error guardando viaje: {r.get('error')}", {**state, "wizard": {}})
    v    = (r["data"][0] if isinstance(r.get("data"), list) else r.get("data")) or {}
    util = float(data.get("precio_venta_viaje") or 0) - float(data.get("costo_viaje") or 0)
    msg  = (f"✅ Viaje <b>{v.get('folio','?')}</b> registrado.\n"
            f"Ruta: {data.get('origen')} → {data.get('destino')}\n"
            f"Cliente: {data.get('cliente')}\n"
            f"Utilidad: ${util:,.0f}")
    if data.get("estatus_pago") == "por_cobrar":
        msg += "\n📋 CXC generada automáticamente."
    return _ok(msg, {**state, "wizard": {}})


def _save_gasto(data: dict, state: dict) -> dict:
    r = svc.crear_gasto(data)
    if not r.get("ok"):
        return _ok(f"Error guardando gasto: {r.get('error')}", {**state, "wizard": {}})
    g   = (r["data"][0] if isinstance(r.get("data"), list) else r.get("data")) or {}
    msg = (f"✅ Gasto <b>{g.get('folio','?')}</b> registrado.\n"
           f"Concepto: {data.get('concepto')}\n"
           f"Monto: ${float(data.get('monto_gasto') or 0):,.0f}\n"
           f"Viaje: {data.get('numero_viaje') or 'sin viaje'}")
    return _ok(msg, {**state, "wizard": {}})


def _save_pago(data: dict, state: dict) -> dict:
    r = svc.crear_pago(data)
    if not r.get("ok"):
        return _ok(f"Error guardando pago: {r.get('error')}", {**state, "wizard": {}})
    p   = (r["data"][0] if isinstance(r.get("data"), list) else r.get("data")) or {}
    msg = (f"✅ Pago <b>{p.get('folio','?')}</b> registrado.\n"
           f"Viaje: {data.get('numero_viaje')}\n"
           f"Monto: ${float(data.get('monto_pago') or 0):,.0f}\n"
           f"Método: {data.get('metodo_pago')}")
    return _ok(msg, {**state, "wizard": {}})


# ─── DOCUMENT EXTRACTION ─────────────────────────────────────────────────────

def _handle_doc(photo, document, wizard: dict, state: dict) -> dict:
    action = wizard.get("action", "viaje")

    if photo:
        file_id    = photo[-1]["file_id"]
        media_type = "image/jpeg"
    else:
        file_id    = document["file_id"]
        media_type = document.get("mime_type", "image/jpeg")

    file_bytes, err = svc.descargar_telegram(file_id)
    if err:
        return _ok(f"Error descargando archivo: {err}", {**state, "wizard": {}})

    schemas = {"viaje": _VIAJE_SCHEMA, "gasto": _GASTO_SCHEMA, "pago": _PAGO_SCHEMA}
    hints   = {
        "viaje": "Documento de viaje de transporte de carga (carta porte, remisión, manifiesto).",
        "gasto": "Ticket o comprobante de gasto operativo (gasolina, caseta, comida, reparación).",
        "pago":  "Comprobante de pago o transferencia bancaria.",
    }

    r = svc.extraer_documento(
        base64.b64encode(file_bytes).decode(),
        media_type,
        schemas.get(action, {}),
        hints.get(action, ""),
    )
    if not r.get("ok"):
        return _ok(f"No pude leer el documento: {r.get('error')}", {**state, "wizard": {}})

    extracted = r.get("extracted", {})
    savers    = {"viaje": _save_viaje, "gasto": _save_gasto, "pago": _save_pago}
    result    = savers.get(action, _save_viaje)(extracted, state)

    # Append extracted fields to confirmation message
    fields = "\n".join(f"  {k}: {v}" for k, v in extracted.items() if v is not None)
    result["response"] = result["response"].replace(
        "✅", f"✅ (desde documento)\n\n{fields}\n\n✅"
    )
    return result


# ─── HELPERS ─────────────────────────────────────────────────────────────────

def _ok(response: str, state: dict, markup: dict | None = None) -> dict:
    r: dict = {"response": response, "state": state}
    if markup:
        r["reply_markup"] = markup
    return r


def _tipo_markup() -> dict:
    return {"inline_keyboard": [[
        {"text": "✍️ Manual",     "callback_data": "manual"},
        {"text": "📷 Imagen/PDF", "callback_data": "imagen"},
    ]]}
