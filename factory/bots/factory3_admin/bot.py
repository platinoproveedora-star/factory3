"""Admin bot for factory3 — generic modal dispatcher."""

from __future__ import annotations

from pathlib import Path

_COMMANDS_DEFAULT = {
    "/start": "Hola! Soy el bot admin de factory3.\nEscribe /ayuda para ver los comandos.",
    "/ayuda": (
        "Comandos disponibles:\n"
        "/start — Iniciar\n"
        "/ayuda — Ayuda\n"
        "/estado — Estado del sistema\n"
        "/rh1 — Entrar al modo Recursos Humanos\n"
        "/logplat — Entrar al modo Logística Platino\n"
        "/fbgroups — Entrar al modo FB Groups Discovery\n"
        "/sales — Entrar al modo Ventas / CRM\n"
        "/timelog — Ver proyectos activos con horas y deadline\n"
        "/timelog UC-101 — Status de un cliente\n"
        "/tiempo UC-101 PROY-001 2.5 notas — Registrar horas\n"
        "/pomodoro start — Iniciar pomodoro 20 min\n"
        "/pomodoro stop — Detener pomodoro\n"
        "/pomodoro — Status del pomodoro\n"
        "/salir — Salir del modo activo"
    ),
    "/estado": "Sistema activo y funcionando.",
}

_MODES = {
    "/rh1":      "rh_1",
    "/logplat":  "logplat",
    "/fbgroups": "fbgroups",
    "/sales":    "sales",
}

_TIMELOG_CMDS = {"/timelog", "/tiempo", "/pomodoro"}

_MODE_SKILLS = {
    "fbgroups": "vertical_fb/fbgroups_run",
    "sales":    "vertical_sales/sales_run",
}


def handle_update(update: dict, state: dict) -> dict:
    message = update.get("message", {})
    text    = (message.get("text") or "").strip()
    mode    = state.get("mode")

    # Timelog y pomodoro — comandos directos sin modo
    cmd_base = text.split()[0] if text else ""
    if cmd_base in _TIMELOG_CMDS:
        return _run_timelog(text, state)

    # Enter a mode
    if text in _MODES:
        new_mode = _MODES[text]
        return {
            "response": f"Modo {new_mode.upper()} activado.",
            "state":    {"mode": new_mode},
            "command":  new_mode,
            "reply_markup": {"inline_keyboard": [[
                {"text": "Ayuda", "callback_data": "/ayuda"},
                {"text": "Vacantes", "callback_data": "/vacantes"},
                {"text": "Status", "callback_data": "/status"},
            ]]},
        }

    # Exit mode
    if text == "/salir":
        if mode:
            return {"response": f"Saliste del modo {mode.upper()}.", "state": {}, "command": "salir"}
        return {"response": "No hay modo activo.", "state": {}, "command": "salir"}

    # Delegate to mode skill
    if mode:
        return _run_mode_skill(mode, update, state)

    # Default admin commands
    response = _COMMANDS_DEFAULT.get(
        text, "Comando no reconocido. Escribe /ayuda para ver los comandos."
    )
    markup = None
    if text in ("/start", "/ayuda"):
        markup = {"inline_keyboard": [
            [
                {"text": "Entrar a RH",       "callback_data": "/rh1"},
                {"text": "Logística Platino", "callback_data": "/logplat"},
            ],
            [
                {"text": "FB Groups",   "callback_data": "/fbgroups"},
                {"text": "Ventas CRM",  "callback_data": "/sales"},
            ],
            [
                {"text": "📋 Proyectos",    "callback_data": "/timelog"},
                {"text": "🍅 Pomodoro",     "callback_data": "/pomodoro start"},
            ],
        ]}
    return {
        "response": response,
        "state":    {},
        "command":  text.lstrip("/") if text.startswith("/") else None,
        "reply_markup": markup,
    }


def _run_timelog(text: str, state: dict) -> dict:
    from factory.engine import SkillLoader, SkillRunner
    base   = Path(__file__).parent.parent.parent.parent
    loader = SkillLoader(
        internal_root=base / "factory" / "skills" / "internos",
        external_root=base / "factory" / "skills" / "externos",
    )
    runner = SkillRunner(loader)
    result = runner.run(
        "vertical_upwork_clients/timelog_run",
        {"text": text, "state": state},
        source="internos",
    )
    if result.get("ok") and result.get("data"):
        data = result["data"]
        return {
            "response": data.get("response", ""),
            "state":    data.get("state", state),
        }
    return {"response": f"Error: {result.get('error', 'desconocido')}", "state": state}


def _run_mode_skill(mode: str, update: dict, state: dict) -> dict:
    from factory.engine import SkillLoader, SkillRunner

    base = Path(__file__).parent.parent.parent.parent  # factory3 root
    ext  = base / "factory" / "skills" / "externos"
    ext.mkdir(parents=True, exist_ok=True)
    loader = SkillLoader(
        internal_root=base / "factory" / "skills" / "internos",
        external_root=ext,
    )
    runner = SkillRunner(loader)
    skill_name = _MODE_SKILLS.get(mode, f"{mode}_run")
    result = runner.run(skill_name, {"update": update, "state": state}, source="internos")

    if result.get("ok") and result.get("data"):
        return result["data"]
    return {
        "response": f"Error en modo {mode}: {result.get('error', 'error desconocido')}",
        "state":    state,
    }
