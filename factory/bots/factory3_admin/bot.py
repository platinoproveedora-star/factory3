"""Admin bot for factory3 — generic modal dispatcher."""

from __future__ import annotations

from pathlib import Path

_COMMANDS_DEFAULT = {
    "/start": (
        "Hola! Soy el bot admin de factory3.\n"
        "Escribe /ayuda para ver los comandos disponibles."
    ),
    "/ayuda": (
        "Comandos disponibles:\n"
        "/start — Iniciar\n"
        "/ayuda — Ayuda\n"
        "/estado — Estado del sistema\n"
        "/rh_1 — Entrar al modo Recursos Humanos\n"
        "/salir — Salir del modo activo"
    ),
    "/estado": "Sistema activo y funcionando.",
}

_MODES = {
    "/rh_1": "rh_1",
}


def handle_update(update: dict, state: dict) -> dict:
    message = update.get("message", {})
    text    = (message.get("text") or "").strip()
    mode    = state.get("mode")

    # Enter a mode
    if text in _MODES:
        new_mode = _MODES[text]
        return {
            "response": (
                f"Modo {new_mode.upper()} activado.\n"
                "Escribe /ayuda para ver los comandos.\n"
                "Escribe /salir para salir."
            ),
            "state":   {"mode": new_mode},
            "command": new_mode,
        }

    # Exit current mode
    if text == "/salir":
        if mode:
            return {"response": f"Saliste del modo {mode.upper()}.", "state": {}, "command": "salir"}
        return {"response": "No hay modo activo.", "state": {}, "command": "salir"}

    # Delegate to mode skill
    if mode:
        return _run_mode_skill(mode, update, state)

    # Default admin commands
    response = _COMMANDS_DEFAULT.get(
        text, "Comando no reconocido. Escribe /ayuda para ver los comandos disponibles."
    )
    return {
        "response": response,
        "state":    {},
        "command":  text.lstrip("/") if text.startswith("/") else None,
    }


def _run_mode_skill(mode: str, update: dict, state: dict) -> dict:
    from factory.engine import SkillLoader, SkillRunner

    base = Path(__file__).parent.parent.parent.parent  # factory3 root
    loader = SkillLoader(
        internal_root=base / "factory" / "skills" / "internos",
        external_root=base / "factory" / "skills" / "externos",
    )
    runner = SkillRunner(loader)
    result = runner.run(f"{mode}_run", {"update": update, "state": state}, source="internos")

    if result.get("ok") and result.get("data"):
        return result["data"]
    return {
        "response": f"Error en modo {mode}: {result.get('error', 'error desconocido')}",
        "state":    state,
    }
