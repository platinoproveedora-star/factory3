"""Handler WhatsApp para Platino Logística — canal-agnostic.

Recibe {type, body, media_id, from_phone, empresa_id} y devuelve {reply}.
La máquina de estados se persiste en public.bot_states con
chat_id = wabiz_logplat_{from_phone}.
"""
from __future__ import annotations

import base64
import importlib.util
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path

_UA = "FactoryFactory/0.1 (+https://github.com/)"

_INTERNOS_DIR = Path(__file__).parent.parent
_LOGPLAT_DIR  = Path(__file__).parent.parent.parent.parent.parent / "EMP_LOGPLAT"

_AYUDA = (
    "*LOGPLAT WhatsApp — Platino Logística*\n\n"
    "*Registrar gasto:*\n"
    "Escribe: gasto\n"
    "Luego: `cantidad,concepto,dd/mm/yy,viaje`\n"
    "Ej: `500,gasolina,12/05/26,25`\n"
    "O envía 📷 foto del comprobante\n\n"
    "*Registrar viaje:*\n"
    "Escribe: viaje\n"
    "Luego: `numero,origen,destino,precio`\n"
    "Ej: `25,merida,cancun,15000`\n"
    "O envía 📄 documento del viaje\n\n"
    "Escribe *ayuda* para ver este mensaje de nuevo."
)

_PROMPTS = {
    "gasto": (
        "Envía el gasto:\n"
        "`cantidad,concepto,dd/mm/yy,viaje`\n"
        "Ej: `500,gasolina,12/05/26,25`\n\n"
        "O envía 📷 foto del comprobante."
    ),
    "viaje": (
        "Envía el viaje:\n"
        "`numero,origen,destino,precio`\n"
        "Ej: `25,merida,cancun,15000`\n\n"
        "O envía 📄 foto/PDF del documento."
    ),
}


# ── LOADERS ──────────────────────────────────────────────────────────────────

def _svc():
    spec = importlib.util.spec_from_file_location("logplat_svc", _LOGPLAT_DIR / "service.py")
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _media_dl():
    path = _INTERNOS_DIR / "vertical_wabiz" / "wabiz_media_downloader" / "service.py"
    spec = importlib.util.spec_from_file_location("wabiz_media_dl", path)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.WabizMediaDownloaderService()


# ── SERVICE ───────────────────────────────────────────────────────────────────

class LogplatMessageHandlerService:

    def ejecutar(self, context: dict) -> dict:
        from_phone = context.get("from_phone", "")
        msg_type   = context.get("type", "text")
        body       = (context.get("body") or "").strip()
        media_id   = context.get("media_id") or ""
        empresa_id = context.get("usuario_empresa_id") or context.get("empresa_id", "logplat")
        chofer     = context.get("usuario_nombre", "")
        dry_run    = context.get("dry_run", True)

        if not from_phone:
            return {"ok": False, "error": "from_phone requerido"}

        state      = self._load_state(from_phone)
        hint       = state.get("hint", "")
        text_lower = body.lower()
        reply      = ""
        new_state  = dict(state)

        # ── Ayuda ─────────────────────────────────────────────────────────────
        if msg_type == "text" and text_lower in ("ayuda", "/ayuda", "help"):
            reply     = _AYUDA
            new_state = {}

        # ── Activar modo gasto ────────────────────────────────────────────────
        elif msg_type == "text" and any(kw in text_lower for kw in ("gasto", "/gasto")):
            new_state = {"hint": "gasto"}
            reply     = _PROMPTS["gasto"]

        # ── Activar modo viaje ────────────────────────────────────────────────
        elif msg_type == "text" and any(kw in text_lower for kw in ("viaje", "/viaje")):
            new_state = {"hint": "viaje"}
            reply     = _PROMPTS["viaje"]

        # ── Pendiente: ligar doc a viaje ──────────────────────────────────────
        elif hint == "viaje_doc_pending":
            reply, new_state = self._handle_doc_link(body, msg_type, state, dry_run)

        # ── Con hint activo: recibir datos ────────────────────────────────────
        elif hint in ("gasto", "viaje"):
            if msg_type in ("image", "document", "video", "audio") and media_id:
                reply, new_state = self._handle_media(media_id, empresa_id, hint, state, dry_run, chofer)
            elif msg_type == "text" and body:
                reply, new_state = self._handle_text(body, hint, state, dry_run, chofer)
            else:
                reply     = _PROMPTS.get(hint, "Envía texto o archivo.")
                new_state = state

        # ── Sin hint: media sin contexto ──────────────────────────────────────
        elif msg_type in ("image", "document") and media_id:
            reply     = "Escribe *gasto* o *viaje* antes de enviar un archivo."
            new_state = state

        # ── Sin hint: texto libre ─────────────────────────────────────────────
        else:
            reply     = "Escribe *gasto* para registrar un gasto, *viaje* para registrar un viaje, o *ayuda*."
            new_state = state

        if not dry_run:
            self._save_state(from_phone, new_state)

        return {"ok": True, "data": {"reply": reply}}

    # ── HANDLERS ──────────────────────────────────────────────────────────────

    def _handle_doc_link(self, body: str, msg_type: str, state: dict, dry_run: bool) -> tuple[str, dict]:
        doc_url  = state.get("doc_url", "")
        doc_name = state.get("doc_name", "")
        if msg_type != "text" or not body:
            return "Escribe el número de viaje para ligar el documento (ej: 22 o VIA-022).", state
        folio = _normalizar_folio(body)
        if not folio:
            return "Escribe el número de viaje (ej: 22 o VIA-022).", state
        if dry_run:
            return f"[dry_run] Ligaría doc a {folio}.", {}
        ok = _svc().agregar_doc_viaje(folio, doc_url, nombre=doc_name)
        if ok:
            return f"✅ Documento guardado en viaje *{folio}*.", {}
        return f"No pude guardar el doc en {folio}. Verifica el número e intenta de nuevo.", state

    def _handle_text(self, text: str, hint: str, state: dict, dry_run: bool, chofer: str = "") -> tuple[str, dict]:
        if hint == "gasto":
            parsed = _parsear_gasto(text, chofer)
            if parsed:
                if dry_run:
                    return f"[dry_run] Gasto: {parsed}", {}
                r = _svc().crear_gasto(parsed)
                return _fmt_gasto(r, parsed), {}
            return (
                "Formato incorrecto.\n\n"
                "Usa: `cantidad,concepto,dd/mm/yy,viaje`\n"
                "Ej: `500,gasolina,12/05/26,25`\n\n"
                "O envía 📷 foto del comprobante.",
                state,
            )

        if hint == "viaje":
            parsed = _parsear_viaje(text, chofer)
            if parsed:
                if dry_run:
                    return f"[dry_run] Viaje: {parsed}", {}
                r = _svc().crear_viaje(parsed)
                return _fmt_viaje(r, parsed), {}
            return (
                "Formato incorrecto.\n\n"
                "Usa: `numero,origen,destino,precio`\n"
                "Ej: `25,merida,cancun,15000`\n\n"
                "O envía 📄 foto/PDF del documento.",
                state,
            )

        return "No entendí. Usa *gasto* o *viaje*.", state

    def _handle_media(self, media_id: str, empresa_id: str, hint: str, state: dict, dry_run: bool, chofer: str = "") -> tuple[str, dict]:
        dl = _media_dl().ejecutar({"media_id": media_id, "empresa_id": empresa_id})
        if not dl.get("ok"):
            return f"Error descargando archivo: {dl.get('error')}", state

        content_b64 = dl["data"]["content_b64"]
        mime_type   = dl["data"]["mime_type"]
        file_bytes  = base64.b64decode(content_b64)
        ext         = (mime_type.split("/")[-1].split(";")[0] or "bin")[:10]
        filename    = f"{media_id}.{ext}"

        if hint == "viaje":
            if dry_run:
                new_state = {**state, "hint": "viaje_doc_pending", "doc_url": "dry_run_url", "doc_name": filename}
                return "[dry_run] Doc subido. ¿A qué número de viaje lo ligo?", new_state
            doc_url, err = _svc().subir_documento(file_bytes, filename, mime_type)
            if not doc_url:
                return f"Error subiendo documento: {err}", state
            new_state = {**state, "hint": "viaje_doc_pending", "doc_url": doc_url, "doc_name": filename}
            return "📎 Documento subido.\n¿A qué número de viaje lo ligo? (ej: 22 o VIA-022)", new_state

        if hint == "gasto":
            if dry_run:
                return "[dry_run] Interpretaría imagen de gasto.", {}
            svc  = _svc()
            r    = svc.interpretar_libre("", content_b64, mime_type, "gasto")
            if not r.get("ok"):
                return f"No pude leer el comprobante: {r.get('error')}", state
            data       = r.get("data", {})
            if chofer:
                data["chofer"] = chofer
            doc_url, _ = svc.subir_documento(file_bytes, filename, mime_type)
            if doc_url:
                data["id_doc"] = doc_url
            gr = svc.crear_gasto(data)
            return _fmt_gasto(gr, data), {}

        return "Envía texto o archivo.", state

    # ── STATE ─────────────────────────────────────────────────────────────────

    def _load_state(self, from_phone: str) -> dict:
        chat_id = f"wabiz_logplat_{from_phone}"
        base    = os.getenv("SUPABASE_URL", "").rstrip("/")
        key     = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        try:
            qs  = urllib.parse.urlencode({
                "chat_id": f"eq.{chat_id}",
                "select":  "state",
                "order":   "updated_at.desc",
                "limit":   "1",
            })
            req = urllib.request.Request(f"{base}/rest/v1/bot_states?{qs}", headers={
                "apikey": key, "Authorization": f"Bearer {key}",
                "Accept": "application/json", "User-Agent": _UA,
            })
            with urllib.request.urlopen(req, timeout=10) as r:
                rows = json.loads(r.read().decode())
                return rows[0].get("state") or {} if rows else {}
        except Exception:
            return {}

    def _save_state(self, from_phone: str, state: dict) -> None:
        chat_id = f"wabiz_logplat_{from_phone}"
        base    = os.getenv("SUPABASE_URL", "").rstrip("/")
        key     = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        headers = {
            "apikey": key, "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
            "User-Agent": _UA,
        }
        try:
            patch_url     = f"{base}/rest/v1/bot_states?chat_id=eq.{urllib.parse.quote(chat_id)}"
            patch_payload = json.dumps({"state": state}).encode()
            req = urllib.request.Request(patch_url, data=patch_payload, method="PATCH", headers=headers)
            with urllib.request.urlopen(req, timeout=10) as r:
                content_range = r.headers.get("Content-Range", "0/0")
                updated = int(content_range.split("/")[-1]) if "/" in content_range else 0

            if updated == 0:
                post_payload = json.dumps({"chat_id": chat_id, "state": state}).encode()
                req = urllib.request.Request(f"{base}/rest/v1/bot_states", data=post_payload, method="POST", headers=headers)
                urllib.request.urlopen(req, timeout=10).close()
        except Exception:
            pass


# ── PARSERS ───────────────────────────────────────────────────────────────────

def _normalizar_folio(texto: str) -> str:
    t = texto.upper().strip()
    m = re.search(r"\d+", t)
    if not m:
        return ""
    return f"VIA-{int(m.group()):03d}"


def _parsear_fecha(texto: str) -> str | None:
    match = re.match(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", texto.strip())
    if not match:
        return None
    d_str, m_str, y_str = match.groups()
    try:
        from datetime import date
        y = int(y_str)
        if y < 100:
            y += 2000
        return date(y, int(m_str), int(d_str)).isoformat()
    except (ValueError, TypeError):
        return None


def _parsear_gasto(texto: str, chofer: str = "") -> dict | None:
    partes = [p.strip() for p in texto.split(",")]
    if len(partes) != 4:
        return None
    cantidad_str, concepto, fecha_str, viaje = partes
    try:
        monto = float(cantidad_str)
    except ValueError:
        return None
    fecha = _parsear_fecha(fecha_str)
    if not fecha:
        return None
    folio = _normalizar_folio(viaje)
    if not folio:
        return None
    return {
        "monto_gasto":  monto,
        "concepto":     concepto,
        "fecha_gasto":  fecha,
        "numero_viaje": folio,
        "chofer":       chofer,
        "empresa_id":   "LOGPLAT",
    }


def _parsear_viaje(texto: str, chofer: str = "") -> dict | None:
    partes = [p.strip() for p in texto.split(",")]
    if len(partes) != 4:
        return None
    numero_str, origen, destino, precio_str = partes
    try:
        numero = int(numero_str)
        precio = float(precio_str)
    except ValueError:
        return None
    return {
        "folio":              f"VIA-{numero:03d}",
        "origen":             origen,
        "destino":            destino,
        "precio_venta_viaje": precio,
        "chofer":             chofer,
        "estatus_pago":       "por_cobrar",
        "empresa_id":         "LOGPLAT",
    }


# ── FORMATTERS ────────────────────────────────────────────────────────────────

def _fmt_gasto(r: dict, data: dict) -> str:
    if not r.get("ok"):
        return f"Error guardando gasto: {r.get('error')}"
    g   = (r["data"][0] if isinstance(r.get("data"), list) else r.get("data")) or {}
    msg = (f"✅ Gasto *{g.get('folio', '?')}* registrado.\n"
           f"Concepto: {data.get('concepto') or '—'}\n"
           f"Monto: ${float(data.get('monto_gasto') or 0):,.0f}\n"
           f"Viaje: {data.get('numero_viaje') or '—'}")
    if data.get("id_doc"):
        msg += "\n📎 Comprobante guardado."
    return msg


def _fmt_viaje(r: dict, data: dict) -> str:
    if not r.get("ok"):
        return f"Error guardando viaje: {r.get('error')}"
    v = (r["data"][0] if isinstance(r.get("data"), list) else r.get("data")) or {}
    return (f"✅ Viaje *{v.get('folio', '?')}* registrado.\n"
            f"Ruta: {data.get('origen', '?')} → {data.get('destino', '?')}\n"
            f"Venta: ${float(data.get('precio_venta_viaje', 0)):,.0f}")
