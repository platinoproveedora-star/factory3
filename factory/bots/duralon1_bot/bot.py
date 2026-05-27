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
    "combustible", "gastos varios", "taller mecanico", "papeleria",
    "telmex", "gas", "internet", "recargas celulares",
    "nomina", "gps", "imss", "sat",
]

_KNOWN_USERS = {
    "8739777586": {"name": "ACH",   "role": "admin"},
    "8555452219": {"name": "Tania", "role": "capturista"},
    # Luis: pendiente
}

_FACTORY_DIR = Path(__file__).resolve().parents[2]

_MENU = (
    "Duralon Gastos — elige como registrar:\n\n"
    "/1  Foto del ticket (OCR automatico)\n"
    "/2  Formato rapido: cantidad,dd/mm/aa,concepto\n"
    "/3  Manual paso a paso\n"
    "/4  Salir\n\n"
    "/resumen   Totales por categoria\n"
    "/mis_gastos  Tus ultimos gastos"
)


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

def _cat_menu(highlight: str = "") -> str:
    lines = []
    for i, c in enumerate(_CATEGORIES):
        mark = " <-" if c == highlight else ""
        lines.append(f"{i+1}. {c}{mark}")
    return "Categoria:\n" + "\n".join(lines) + "\n\nEscribe el numero."

def _cat_from_input(text: str) -> str | None:
    t = text.strip()
    if t.isdigit():
        idx = int(t) - 1
        if 0 <= idx < len(_CATEGORIES):
            return _CATEGORIES[idx]
        return None
    low = t.lower()
    return low if low in _CATEGORIES else None

def _parse_date(s: str) -> str | None:
    for fmt in ("%d/%m/%y", "%d/%m/%Y"):
        try:
            return datetime.strptime(s.strip(), fmt).date().isoformat()
        except ValueError:
            pass
    return None

def _detect_forma1(text: str) -> dict | None:
    parts = [p.strip() for p in text.split(",")]
    if len(parts) < 3:
        return None
    try:
        monto = float(parts[0])
    except ValueError:
        return None
    fecha = _parse_date(parts[1])
    if not fecha:
        return None
    descripcion = ",".join(parts[2:]).strip()
    if not descripcion:
        return None
    return {"monto": monto, "fecha": fecha, "descripcion": descripcion}


# ---------------------------------------------------------------------------
# Save helper
# ---------------------------------------------------------------------------

def _do_save(update: dict, draft: dict) -> dict:
    chat_id = _chat_id(update)
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
        "usuario_id":     user.get("id") if isinstance(user, dict) else "",
        "categoria":      draft["categoria"],
        "monto":          draft["monto"],
        "descripcion":    draft.get("descripcion", ""),
        "fecha":          draft.get("fecha") or date.today().isoformat(),
        "metodo_captura": draft.get("metodo_captura", "manual"),
    })

    # Subir foto si existe (captura OCR)
    if save.get("ok") and draft.get("photo_b64"):
        gasto_id = (save.get("data", {}).get("gasto") or {}).get("id", "")
        file_id  = draft.get("photo_file_id", "ticket")
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
    token = os.getenv("UC101_PROY001_BOT_TOKEN", "")
    if not token:
        return None, "Token no configurado"
    try:
        with urllib.request.urlopen(
            f"https://api.telegram.org/bot{token}/getFile?file_id={file_id}", timeout=10
        ) as r:
            data = json.loads(r.read())
        if not data.get("ok"):
            return None, "getFile fallo"
        file_path = data["result"]["file_path"]
        with urllib.request.urlopen(
            f"https://api.telegram.org/file/bot{token}/{file_path}", timeout=30
        ) as r:
            return r.read(), None
    except Exception as e:
        return None, str(e)


def _handle_photo(update: dict, state: dict) -> dict:
    photos = (update.get("message") or {}).get("photo", [])
    if not photos:
        return {"response": "No se recibio la foto.", "state": state}

    file_id    = photos[-1]["file_id"]
    file_bytes, err = _download_telegram_photo(file_id)

    if err or not file_bytes:
        return {
            "response": f"No pude descargar la foto ({err}).\nUsa /3 para captura manual.",
            "state": state, "command": "photo_download_error",
        }

    content_b64 = base64.b64encode(file_bytes).decode()
    ocr = _run_expenses("ocr_ticket", {
        "content_b64": content_b64,
        "media_type":  "image/jpeg",
        "categories":  _CATEGORIES,
    })

    if not ocr.get("ok"):
        return {
            "response": (
                f"No pude leer el ticket: {ocr.get('error','error')}\n"
                "Usa /2 para formato rapido o /3 para manual."
            ),
            "state": state, "command": "ocr_failed",
        }

    data    = ocr.get("data", {})
    monto   = data.get("monto")
    fecha   = data.get("fecha") or date.today().isoformat()
    desc    = data.get("descripcion", "")
    cat_sug = data.get("categoria_sugerida", "")

    if not monto:
        return {
            "response": (
                "No detecto el monto en el ticket.\n"
                "Usa /2 para formato rapido o /3 para manual."
            ),
            "state": state, "command": "ocr_no_monto",
        }

    draft = {
        "monto":          float(monto),
        "fecha":          fecha,
        "descripcion":    desc,
        "metodo_captura": "ai_ocr",
        "photo_b64":      content_b64,
        "photo_file_id":  file_id,
    }

    return {
        "response": (
            f"Ticket detectado:\n"
            f"Monto: ${draft['monto']:,.0f}\n"
            f"Fecha: {fecha}\n"
            f"Descripcion: {desc or '(no detectada)'}\n\n"
            + _cat_menu(highlight=cat_sug)
        ),
        "state":   {**state, "flow": "fast_expense", "step": "category", "draft": draft},
        "command": "ocr_ok",
    }


# ---------------------------------------------------------------------------
# Comandos
# ---------------------------------------------------------------------------

def _start(update: dict, state: dict) -> dict:
    name = _user_label(_chat_id(update), _first_name(update))
    return {
        "response": f"Hola {name}! Bot de gastos Duralon.\n\n{_MENU}",
        "state":    {**state, "last_chat_id": _chat_id(update)},
        "command":  "start",
    }

def _cmd_foto(state: dict) -> dict:
    return {
        "response": "Manda la foto del ticket directamente aqui.",
        "state":    {**state, "flow": "waiting_photo"},
        "command":  "cmd_foto",
    }

def _cmd_formato(state: dict) -> dict:
    return {
        "response": (
            "Formato rapido — manda directo:\n"
            "  cantidad,dd/mm/aa,concepto\n\n"
            "Ejemplo:\n"
            "  1250,27/05/26,gasolina unidad 12\n\n"
            "El bot te pregunta la categoria."
        ),
        "state":   state,
        "command": "cmd_formato",
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
    data  = result.get("data") or {}
    lines = [f"  {cat}: ${monto:,.0f}" for cat, monto in (data.get("por_categoria") or {}).items()]
    body  = "\n".join(lines) if lines else "  Sin gastos aun."
    return {
        "response": f"Resumen\nTotal: ${data.get('total', 0):,.0f} ({data.get('num_gastos', 0)} movimientos)\n\n{body}",
        "state":    state, "command": "resumen",
    }

def _my_expenses(update: dict, state: dict) -> dict:
    user_result = _run_expenses("get_user", {"telegram_chat_id": _chat_id(update)})
    if not user_result.get("ok") or not user_result.get("data", {}).get("user"):
        return {"response": "Aun no tienes gastos. Usa /1, /2 o /3.", "state": state}
    user   = user_result["data"]["user"]
    result = _run_expenses("list_expenses", {"usuario_id": user["id"], "limit": 5})
    rows   = (result.get("data") or {}).get("gastos") or []
    if not rows:
        return {"response": "Aun no tienes gastos registrados.", "state": state}
    lines  = [f"{g.get('folio')} | ${float(g.get('monto',0)):,.0f} | {g.get('fecha')}" for g in rows]
    return {"response": "Tus ultimos gastos:\n" + "\n".join(lines), "state": state, "command": "mis_gastos"}


# ---------------------------------------------------------------------------
# Flujo manual paso a paso
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
        draft["descripcion"]    = "" if text == "." else text
        draft["metodo_captura"] = "manual"
        save = _do_save(update, draft)
        if not save.get("ok"):
            return {"response": f"Error guardando: {save.get('error', 'desconocido')}", "state": {}, "command": "save_failed"}
        folio = save.get("data", {}).get("folio", "")
        return {"response": f"Guardado {folio}  ${draft['monto']:,.0f}  {draft['categoria']}", "state": {}, "command": "saved"}

    return {"response": f"Algo fallo. Usa /3 para empezar de nuevo.\n\n{_MENU}", "state": {}}


# ---------------------------------------------------------------------------
# Forma rapida con comas
# ---------------------------------------------------------------------------

def _handle_forma1(update: dict, state: dict, parsed: dict) -> dict:
    return {
        "response": _cat_menu(),
        "state":    {**state, "flow": "fast_expense", "step": "category", "draft": parsed},
        "command":  "forma1_parsed",
    }

def _handle_fast_category(update: dict, state: dict) -> dict:
    text  = _text(update)
    draft = state.get("draft") or {}
    cat   = _cat_from_input(text)
    if not cat:
        return {"response": f"Numero invalido.\n\n{_cat_menu()}", "state": state}
    draft["categoria"]     = cat
    draft["metodo_captura"] = draft.get("metodo_captura", "manual")
    save = _do_save(update, draft)
    if not save.get("ok"):
        return {"response": f"Error guardando: {save.get('error', 'desconocido')}", "state": {}, "command": "save_failed"}
    folio = save.get("data", {}).get("folio", "")
    metodo_icon = "📸" if draft.get("metodo_captura") == "ai_ocr" else "✅"
    return {
        "response": f"{metodo_icon} Guardado {folio}  ${draft['monto']:,.0f}  {cat}  {draft.get('fecha','')}",
        "state":    {}, "command": "saved",
    }


# ---------------------------------------------------------------------------
# Router principal
# ---------------------------------------------------------------------------

def handle_update(update: dict, state: dict) -> dict:
    state = state or {}
    text  = _text(update)

    # Cancelar siempre
    if text.lower() in {"/cancelar", "cancelar", "/4", "4"}:
        return {"response": f"Hasta luego!\n\n{_MENU}", "state": {}, "command": "salir"}

    # Flujo manual en curso
    if state.get("flow") == "manual_expense" and not text.startswith("/"):
        return _handle_manual_capture(update, state)

    # Forma rapida en curso (esperando categoria)
    if state.get("flow") == "fast_expense" and state.get("step") == "category" and not text.startswith("/"):
        return _handle_fast_category(update, state)

    # Esperando foto (/1)
    if state.get("flow") == "waiting_photo":
        if (update.get("message") or {}).get("photo"):
            return _handle_photo(update, {**state, "flow": None})
        if not text.startswith("/"):
            return {"response": "Manda la foto del ticket, o /4 para salir.", "state": state}

    # Comandos de menu
    if text in {"/start", "start"}:
        return _start(update, state)
    if text in {"/1"}:
        return _cmd_foto(state)
    if text in {"/2"}:
        return _cmd_formato(state)
    if text in {"/3", "/nuevo", "nuevo"}:
        return _start_manual_capture(state)
    if text in {"/ayuda", "ayuda", "/help"}:
        return {"response": _MENU, "state": state, "command": "ayuda"}
    if text in {"/resumen", "resumen"}:
        return _summary(state)
    if text in {"/mis_gastos", "mis_gastos"}:
        return _my_expenses(update, state)

    # Foto directa (sin /1)
    if (update.get("message") or {}).get("photo"):
        return _handle_photo(update, state)

    # Forma rapida: detectar cantidad,fecha,concepto
    if "," in text:
        parsed = _detect_forma1(text)
        if parsed:
            return _handle_forma1(update, state, parsed)

    return {
        "response": _MENU,
        "state":    state,
        "command":  "fallback",
    }
