from __future__ import annotations

import base64
import json
import os
import urllib.request
from datetime import datetime, date
from pathlib import Path

from factory.engine import SkillLoader, SkillRunner


_CLIENT_ID    = "UC-101"
_PROJECT_CODE = "PROY-001"
_SCHEMA       = "uc101_proy001"
_BUCKET       = "uc101-proy001-assets"
_SKILL        = "vertical_client_expenses/client_expenses_run"

_CATEGORIES = [
    "combustible",
    "gastos varios",
    "taller mecanico",
    "papeleria",
    "telmex",
    "gas",
    "internet",
    "recargas celulares",
    "nomina",
    "gps",
    "imss",
    "sat",
]

_KNOWN_USERS = {
    "8739777586": {"name": "ACH",   "role": "admin"},
    "8555452219": {"name": "Tania", "role": "capturista"},  # USR-002
    # Luis: pendiente — agregar cuando se tenga su chat ID.
}

_FACTORY_DIR = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _text(update: dict) -> str:
    return (update.get("message") or {}).get("text", "").strip()

def _chat_id(update: dict) -> str:
    return str((update.get("message") or {}).get("chat", {}).get("id", ""))

def _first_name(update: dict) -> str:
    return (update.get("message") or {}).get("from", {}).get("first_name", "") or ""

def _runner() -> SkillRunner:
    skills_dir = _FACTORY_DIR / "skills"
    loader = SkillLoader(
        internal_root=skills_dir / "internos",
        external_root=skills_dir / "externos",
        extra_roots={"meta": skills_dir / "meta", "eval": skills_dir / "eval"},
    )
    return SkillRunner(loader)

def _run_expenses(action: str, context: dict) -> dict:
    payload = {
        "action":       action,
        "client_id":    _CLIENT_ID,
        "project_code": _PROJECT_CODE,
        "schema":       _SCHEMA,
        "bucket":       _BUCKET,
        "dry_run":      False,
        **context,
    }
    return _runner().run(_SKILL, payload, source="internos")

def _user_label(chat_id: str, fallback: str) -> str:
    known = _KNOWN_USERS.get(chat_id)
    return known["name"] if known else (fallback or f"usuario {chat_id}")

def _cat_menu() -> str:
    lines = "\n".join(f"{i+1}. {c}" for i, c in enumerate(_CATEGORIES))
    return f"Categoria:\n{lines}\n\nEscribe el numero."

def _cat_from_input(text: str) -> str | None:
    """Acepta numero (1-12) o nombre exacto."""
    t = text.strip()
    if t.isdigit():
        idx = int(t) - 1
        if 0 <= idx < len(_CATEGORIES):
            return _CATEGORIES[idx]
        return None
    low = t.lower()
    return low if low in _CATEGORIES else None

def _parse_date(s: str) -> str | None:
    """dd/mm/yy o dd/mm/yyyy → YYYY-MM-DD"""
    for fmt in ("%d/%m/%y", "%d/%m/%Y"):
        try:
            return datetime.strptime(s.strip(), fmt).date().isoformat()
        except ValueError:
            pass
    return None

def _detect_forma1(text: str) -> dict | None:
    """
    Detecta formato rapido: cantidad,dd/mm/yy,concepto
    Retorna dict con monto/fecha/descripcion o None si no aplica.
    """
    parts = [p.strip() for p in text.split(",")]
    if len(parts) < 3:
        return None
    # campo 0: monto
    try:
        monto = float(parts[0].replace(".", "").replace(",", ".") if "," not in parts[0] else parts[0])
        monto = float(parts[0])
    except ValueError:
        return None
    # campo 1: fecha
    fecha = _parse_date(parts[1])
    if not fecha:
        return None
    # campo 2+: concepto (puede tener comas internas)
    descripcion = ",".join(parts[2:]).strip()
    if not descripcion:
        return None
    return {"monto": monto, "fecha": fecha, "descripcion": descripcion}


# ---------------------------------------------------------------------------
# Save helper (compartido por ambas formas)
# ---------------------------------------------------------------------------

def _do_save(update: dict, draft: dict) -> dict:
    chat_id = _chat_id(update)
    # Obtener o registrar usuario
    user_result = _run_expenses("get_user", {"telegram_chat_id": chat_id})
    if not user_result.get("ok") or not user_result.get("data", {}).get("user"):
        name = _user_label(chat_id, _first_name(update))
        reg  = _run_expenses("register_user", {"telegram_chat_id": chat_id, "nombre": name})
        if not reg.get("ok"):
            return {"ok": False, "error": reg.get("error", "no se pudo registrar usuario")}
        user = reg.get("data", {}).get("user")
    else:
        user = user_result["data"]["user"]

    save = _run_expenses("save_expense", {
        "usuario_id":    user.get("id") if isinstance(user, dict) else "",
        "categoria":     draft["categoria"],
        "monto":         draft["monto"],
        "descripcion":   draft.get("descripcion", ""),
        "fecha":         draft.get("fecha") or date.today().isoformat(),
        "metodo_captura": draft.get("metodo_captura", "manual"),
    })

    # Si hay foto de ticket, subirla a Storage y ligarla al gasto
    if save.get("ok") and draft.get("photo_b64"):
        gasto_id  = (save.get("data", {}).get("gasto") or {}).get("id", "")
        file_id   = draft.get("photo_file_id", "ticket")
        _run_expenses("upload_document", {
            "content_b64": draft["photo_b64"],
            "media_type":  "image/jpeg",
            "gasto_id":    gasto_id,
            "filename":    f"{file_id}.jpg",
        })

    return save


# ---------------------------------------------------------------------------
# OCR helpers
# ---------------------------------------------------------------------------

def _download_telegram_photo(file_id: str) -> tuple[bytes | None, str | None]:
    """Descarga foto de Telegram por file_id. Retorna (bytes, None) o (None, error)."""
    token = os.getenv("UC101_PROY001_BOT_TOKEN", "")
    if not token:
        return None, "Token no configurado"
    try:
        with urllib.request.urlopen(
            f"https://api.telegram.org/bot{token}/getFile?file_id={file_id}", timeout=10
        ) as r:
            data = json.loads(r.read())
        if not data.get("ok"):
            return None, "getFile falló"
        file_path = data["result"]["file_path"]
        with urllib.request.urlopen(
            f"https://api.telegram.org/file/bot{token}/{file_path}", timeout=30
        ) as r:
            return r.read(), None
    except Exception as e:
        return None, str(e)


def _handle_photo(update: dict, state: dict) -> dict:
    """Maneja foto/ticket: descarga → OCR con Haiku → flujo de categoria."""
    photos = (update.get("message") or {}).get("photo", [])
    if not photos:
        return {"response": "No se recibio la foto.", "state": state}

    # Mayor resolución = último elemento de la lista
    best   = photos[-1]
    file_id = best["file_id"]

    # Descarga
    file_bytes, err = _download_telegram_photo(file_id)
    if err or not file_bytes:
        return {
            "response": f"No pude descargar la foto ({err}).\nUsa /nuevo o el formato rapido.",
            "state":   state, "command": "photo_download_error",
        }

    content_b64 = base64.b64encode(file_bytes).decode()

    # OCR con Haiku Vision
    ocr = _run_expenses("ocr_ticket", {
        "content_b64": content_b64,
        "media_type":  "image/jpeg",
        "categories":  _CATEGORIES,
    })

    if not ocr.get("ok"):
        return {
            "response": (
                f"No pude leer el ticket: {ocr.get('error','error desconocido')}\n"
                "Usa /nuevo o el formato rapido: cantidad,dd/mm/aa,concepto"
            ),
            "state": state, "command": "ocr_failed",
        }

    data     = ocr.get("data", {})
    monto    = data.get("monto")
    fecha    = data.get("fecha") or date.today().isoformat()
    desc     = data.get("descripcion", "")
    cat_sug  = data.get("categoria_sugerida", "")

    if not monto:
        return {
            "response": (
                "No detecto el monto en el ticket.\n"
                "Usa /nuevo o formato rapido: cantidad,dd/mm/aa,concepto"
            ),
            "state": state, "command": "ocr_no_monto",
        }

    draft = {
        "monto":          float(monto),
        "fecha":          fecha,
        "descripcion":    desc,
        "metodo_captura": "ai_ocr",
        "photo_b64":      content_b64,   # para subirlo al guardar
        "photo_file_id":  file_id,
    }

    # Menu de categorias con sugerida marcada
    lines = []
    for i, c in enumerate(_CATEGORIES):
        mark = " <-" if c == cat_sug else ""
        lines.append(f"{i+1}. {c}{mark}")

    resumen = (
        f"Ticket detectado:\n"
        f"Monto: ${draft['monto']:,.0f}\n"
        f"Fecha: {fecha}\n"
        f"Descripcion: {desc or '(no detectada)'}\n\n"
        "Elige la categoria:\n" + "\n".join(lines)
    )

    return {
        "response": resumen,
        "state":    {**state, "flow": "fast_expense", "step": "category", "draft": draft},
        "command":  "ocr_ok",
    }


# ---------------------------------------------------------------------------
# Comandos
# ---------------------------------------------------------------------------

def _help() -> str:
    cats = "\n".join(f"{i+1}. {c}" for i, c in enumerate(_CATEGORIES))
    return (
        "Duralon Gastos\n\n"
        "Forma rapida — manda directo:\n"
        "  cantidad,dd/mm/aa,concepto\n"
        "  Ej: 1250,27/05/26,gasolina unidad 12\n\n"
        "Paso a paso:\n"
        "  /nuevo\n\n"
        "Otros:\n"
        "  /resumen — totales por categoria\n"
        "  /mis_gastos — tus ultimos 5 gastos\n"
        "  /cancelar — cancela captura en curso\n\n"
        f"Categorias:\n{cats}"
    )

def _start(update: dict, state: dict) -> dict:
    name = _user_label(_chat_id(update), _first_name(update))
    return {
        "response": (
            f"Hola {name}. Bot de gastos Duralon listo.\n\n"
            "Forma rapida: manda  cantidad,dd/mm/aa,concepto\n"
            "Ej: 1250,27/05/26,gasolina unidad 12\n\n"
            "O usa /nuevo para captura paso a paso."
        ),
        "state":   {**state, "last_chat_id": _chat_id(update)},
        "command": "start",
    }

def _start_manual_capture(state: dict) -> dict:
    return {
        "response": "Monto del gasto:",
        "state":    {**state, "flow": "manual_expense", "step": "amount", "draft": {}},
        "command":  "nuevo",
    }

def _summary(state: dict) -> dict:
    result = _run_expenses("get_stats", {})
    if not result.get("ok"):
        return {"response": f"Error: {result.get('error', 'desconocido')}", "state": state}
    data = result.get("data") or {}
    lines = [f"  {cat}: ${monto}" for cat, monto in (data.get("por_categoria") or {}).items()]
    body  = "\n".join(lines) if lines else "  Sin gastos aun."
    return {
        "response": f"Resumen\nTotal: ${data.get('total', 0)} ({data.get('num_gastos', 0)} movimientos)\n\n{body}",
        "state":    state,
        "command":  "resumen",
    }

def _my_expenses(update: dict, state: dict) -> dict:
    user_result = _run_expenses("get_user", {"telegram_chat_id": _chat_id(update)})
    if not user_result.get("ok") or not user_result.get("data", {}).get("user"):
        return {"response": "Aun no tienes gastos. Usa /nuevo o manda uno en forma rapida.", "state": state}
    user   = user_result["data"]["user"]
    result = _run_expenses("list_expenses", {"usuario_id": user["id"], "limit": 5})
    rows   = (result.get("data") or {}).get("gastos") or []
    if not rows:
        return {"response": "Aun no tienes gastos registrados.", "state": state}
    lines  = [f"{g.get('folio')} | ${g.get('monto')} | {g.get('fecha')}" for g in rows]
    return {"response": "Tus ultimos gastos:\n" + "\n".join(lines), "state": state, "command": "mis_gastos"}


# ---------------------------------------------------------------------------
# Flujo paso a paso (Forma 2)
# ---------------------------------------------------------------------------

def _handle_manual_capture(update: dict, state: dict) -> dict:
    text  = _text(update)
    draft = state.get("draft") or {}
    step  = state.get("step")

    if step == "amount":
        try:
            draft["monto"] = float(text)
        except ValueError:
            return {"response": "Monto invalido. Escribe solo el numero, ej: 1250", "state": state}
        return {"response": _cat_menu(), "state": {**state, "step": "category", "draft": draft}}

    if step == "category":
        cat = _cat_from_input(text)
        if not cat:
            return {"response": f"No reconozco esa opcion.\n\n{_cat_menu()}", "state": state}
        draft["categoria"] = cat
        return {
            "response": "Descripcion corta (o manda un punto '.' para omitir):",
            "state":    {**state, "step": "description", "draft": draft},
        }

    if step == "description":
        draft["descripcion"]   = "" if text == "." else text
        draft["metodo_captura"] = "manual"
        save = _do_save(update, draft)
        if not save.get("ok"):
            return {"response": f"Error guardando: {save.get('error', 'desconocido')}", "state": {}, "command": "save_failed"}
        folio = save.get("data", {}).get("folio", "")
        return {"response": f"✅ Guardado {folio}  ${draft['monto']}  {draft['categoria']}", "state": {}, "command": "saved"}

    return {"response": "Algo fallo. Usa /nuevo para empezar.", "state": {}}


# ---------------------------------------------------------------------------
# Forma 1 — captura rapida con comas
# ---------------------------------------------------------------------------

def _handle_forma1(update: dict, state: dict, parsed: dict) -> dict:
    """Primera parte: ya tenemos monto/fecha/descripcion, pedimos categoria."""
    return {
        "response": _cat_menu(),
        "state": {
            **state,
            "flow":  "fast_expense",
            "step":  "category",
            "draft": parsed,
        },
        "command": "forma1_parsed",
    }

def _handle_fast_category(update: dict, state: dict) -> dict:
    """Segunda parte de forma 1: recibe el numero de categoria y guarda."""
    text  = _text(update)
    draft = state.get("draft") or {}
    cat   = _cat_from_input(text)
    if not cat:
        return {"response": f"Numero invalido.\n\n{_cat_menu()}", "state": state}
    draft["categoria"]    = cat
    draft["metodo_captura"] = "manual"
    save = _do_save(update, draft)
    if not save.get("ok"):
        return {"response": f"Error guardando: {save.get('error', 'desconocido')}", "state": {}, "command": "save_failed"}
    folio = save.get("data", {}).get("folio", "")
    return {
        "response": f"✅ Guardado {folio}  ${draft['monto']}  {cat}  {draft.get('fecha','')}",
        "state":    {},
        "command":  "saved",
    }


# ---------------------------------------------------------------------------
# Router principal
# ---------------------------------------------------------------------------

def handle_update(update: dict, state: dict) -> dict:
    state = state or {}
    text  = _text(update)

    # Cancelar siempre
    if text.lower() in {"/cancelar", "cancelar"}:
        return {"response": "Captura cancelada.", "state": {}, "command": "cancelar"}

    # Forma 2 en curso — paso a paso
    if state.get("flow") == "manual_expense" and not text.startswith("/"):
        return _handle_manual_capture(update, state)

    # Forma 1 en curso — esperando categoria
    if state.get("flow") == "fast_expense" and not text.startswith("/"):
        return _handle_fast_category(update, state)

    # Comandos
    if text in {"/start", "start"}:
        return _start(update, state)
    if text in {"/ayuda", "ayuda", "/help"}:
        return {"response": _help(), "state": state, "command": "ayuda"}
    if text in {"/nuevo", "nuevo"}:
        return _start_manual_capture(state)
    if text in {"/resumen", "resumen"}:
        return _summary(state)
    if text in {"/mis_gastos", "mis_gastos"}:
        return _my_expenses(update, state)

    # Forma 1 — detectar cantidad,fecha,concepto
    if "," in text:
        parsed = _detect_forma1(text)
        if parsed:
            return _handle_forma1(update, state, parsed)

    # Foto — OCR con Haiku Vision
    if (update.get("message") or {}).get("photo"):
        return _handle_photo(update, state)

    return {
        "response": "Forma rapida: cantidad,dd/mm/aa,concepto\nO usa /nuevo  |  /ayuda",
        "state":    state,
        "command":  "fallback",
    }
