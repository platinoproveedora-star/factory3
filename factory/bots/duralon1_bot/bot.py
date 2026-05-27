from __future__ import annotations

from pathlib import Path

from factory.engine import SkillLoader, SkillRunner


_CLIENT_ID = "UC-101"
_PROJECT_CODE = "PROY-001"
_SCHEMA = "uc101_proy001"
_BUCKET = "uc101-proy001-assets"
_SKILL = "vertical_client_expenses/client_expenses_run"

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
    "8739777586": {"name": "ACH", "role": "test_user"},
}

_FACTORY_DIR = Path(__file__).resolve().parents[2]


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
        "action": action,
        "client_id": _CLIENT_ID,
        "project_code": _PROJECT_CODE,
        "schema": _SCHEMA,
        "bucket": _BUCKET,
        "dry_run": False,
        **context,
    }
    return _runner().run(_SKILL, payload, source="internos")


def _user_label(chat_id: str, fallback: str) -> str:
    known = _KNOWN_USERS.get(chat_id)
    return known["name"] if known else (fallback or f"usuario {chat_id}")


def _help() -> str:
    return (
        "Duralon Gastos listo.\n\n"
        "Comandos:\n"
        "/nuevo - capturar gasto manual\n"
        "/resumen - ver resumen de gastos\n"
        "/mis_gastos - ver ultimos gastos tuyos\n"
        "/ayuda - ver esta ayuda\n\n"
        "Tambien puedes mandar una foto del ticket; la lectura con AI/OCR queda como siguiente paso del MVP."
    )


def _start(update: dict, state: dict) -> dict:
    chat_id = _chat_id(update)
    name = _user_label(chat_id, _first_name(update))
    response = (
        f"Hola {name}. Soy el bot de gastos de Duralon.\n\n"
        "Ya puedo recibir capturas manuales y consultar informacion del proyecto. "
        "Para empezar usa /nuevo."
    )
    return {"response": response, "state": {**state, "last_chat_id": chat_id}, "command": "start"}


def _start_manual_capture(state: dict) -> dict:
    return {
        "response": "Va. Captura manual: dime el monto del gasto. Ejemplo: 1250.50",
        "state": {**state, "flow": "manual_expense", "step": "amount", "draft": {}},
        "command": "nuevo",
    }


def _handle_manual_capture(update: dict, state: dict) -> dict:
    text = _text(update)
    chat_id = _chat_id(update)
    draft = state.get("draft") or {}
    step = state.get("step")

    if text.lower() in {"/cancelar", "cancelar"}:
        return {"response": "Captura cancelada.", "state": {}, "command": "cancelar"}

    if step == "amount":
        try:
            amount = float(text.replace(",", "."))
        except ValueError:
            return {"response": "No pude leer el monto. Mandamelo como numero, ejemplo: 1250.50", "state": state}
        draft["monto"] = amount
        cats = "\n".join(f"- {cat}" for cat in _CATEGORIES)
        return {"response": f"Categoria del gasto:\n{cats}", "state": {**state, "step": "category", "draft": draft}}

    if step == "category":
        category = text.lower()
        if category not in _CATEGORIES:
            return {"response": "No reconozco esa categoria. Escribe una de la lista tal cual.", "state": state}
        draft["categoria"] = category
        return {"response": "Descripcion corta del gasto. Ejemplo: gasolina unidad 12", "state": {**state, "step": "description", "draft": draft}}

    if step == "description":
        draft["descripcion"] = text
        user_result = _run_expenses("get_user", {"telegram_chat_id": chat_id})
        if not user_result.get("ok") or not user_result.get("data", {}).get("user"):
            name = _user_label(chat_id, _first_name(update))
            reg = _run_expenses("register_user", {"telegram_chat_id": chat_id, "nombre": name})
            if not reg.get("ok"):
                return {
                    "response": (
                        "Tengo la captura, pero aun no pude guardar porque falta configurar Supabase/schema "
                        f"o registrar el usuario. Error: {reg.get('error', reg.get('message', 'desconocido'))}"
                    ),
                    "state": {},
                    "command": "save_failed",
                }
            user = reg.get("data", {}).get("user")
        else:
            user = user_result.get("data", {}).get("user")

        save = _run_expenses("save_expense", {
            "usuario_id": user.get("id") if isinstance(user, dict) else "",
            "categoria": draft["categoria"],
            "monto": draft["monto"],
            "descripcion": draft.get("descripcion", ""),
            "metodo_captura": "manual",
        })
        if not save.get("ok"):
            return {
                "response": f"No pude guardar el gasto todavia. Error: {save.get('error', save.get('message', 'desconocido'))}",
                "state": {},
                "command": "save_failed",
            }
        folio = save.get("data", {}).get("folio", "sin folio")
        return {"response": f"Gasto guardado: {folio}.", "state": {}, "command": "saved"}

    return {"response": "La captura se desordeno. Usa /nuevo para empezar otra vez.", "state": {}}


def _summary(state: dict) -> dict:
    result = _run_expenses("get_stats", {})
    if not result.get("ok"):
        return {"response": f"Aun no puedo consultar el resumen. Error: {result.get('error', result.get('message', 'desconocido'))}", "state": state}
    data = result.get("data") or {}
    response = f"Resumen de gastos\nTotal: ${data.get('total', 0)}\nMovimientos: {data.get('num_gastos', 0)}"
    return {"response": response, "state": state, "command": "resumen"}


def _my_expenses(update: dict, state: dict) -> dict:
    user_result = _run_expenses("get_user", {"telegram_chat_id": _chat_id(update)})
    if not user_result.get("ok") or not user_result.get("data", {}).get("user"):
        return {"response": "Todavia no te encuentro registrado en usuarios. Usa /nuevo para crear tu primer gasto.", "state": state}
    user = user_result["data"]["user"]
    result = _run_expenses("list_expenses", {"usuario_id": user["id"], "limit": 5})
    if not result.get("ok"):
        return {"response": f"No pude listar tus gastos. Error: {result.get('error', result.get('message', 'desconocido'))}", "state": state}
    rows = result.get("data", {}).get("gastos") or []
    if not rows:
        return {"response": "Aun no tienes gastos registrados.", "state": state}
    lines = [f"{g.get('folio')} | ${g.get('monto')} | {g.get('fecha')}" for g in rows]
    return {"response": "Tus ultimos gastos:\n" + "\n".join(lines), "state": state, "command": "mis_gastos"}


def handle_update(update: dict, state: dict) -> dict:
    state = state or {}
    text = _text(update)

    if state.get("flow") == "manual_expense" and not text.startswith("/"):
        return _handle_manual_capture(update, state)

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

    if (update.get("message") or {}).get("photo"):
        return {
            "response": "Recibi la imagen. La lectura AI/OCR va en el siguiente paso; por ahora usa /nuevo para captura manual.",
            "state": state,
            "command": "photo_received",
        }

    return {
        "response": "Te leo. Para capturar un gasto usa /nuevo. Para opciones usa /ayuda.",
        "state": state,
        "command": "fallback",
    }
