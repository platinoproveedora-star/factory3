"""Estoiko Lab bot — demo de chat agents con IA para clientes."""
from __future__ import annotations

import os
from pathlib import Path

# factory3 root (4 niveles desde bots/estoikolab_bot/bot.py)
_BASE = Path(__file__).parent.parent.parent.parent

_DEFAULT_AGENT = os.getenv("ESTOIKOLAB_DEFAULT_AGENT", "AGT-001")

_WELCOME = (
    "👋 ¡Hola! Bienvenido al demo de <b>Estoiko Lab</b>.\n\n"
    "Aquí puedes conversar con un agente de IA configurado para tu negocio.\n\n"
    "Escríbeme lo que necesitas y te atiendo.\n\n"
    "<b>Comandos:</b>\n"
    "/nuevo — reiniciar conversación\n"
    "/agente — ver agente activo"
)


def _get_runner():
    from factory.engine import SkillLoader, SkillRunner
    ext = _BASE / "factory" / "skills" / "externos"
    ext.mkdir(parents=True, exist_ok=True)
    loader = SkillLoader(
        internal_root=_BASE / "factory" / "skills" / "internos",
        external_root=ext,
    )
    return SkillRunner(loader)


def handle_update(update: dict, state: dict) -> dict:
    message  = update.get("message", {})
    text     = (message.get("text") or "").strip()
    agent_id = state.get("agent_id", _DEFAULT_AGENT)
    history  = state.get("history") or []

    # /start o /inicio
    if text in ("/start", "/inicio"):
        return {
            "response": _WELCOME,
            "state":    {"agent_id": agent_id, "history": []},
        }

    # /nuevo — reinicia conversación
    if text == "/nuevo":
        return {
            "response": "✅ Conversación reiniciada. Escríbeme algo.",
            "state":    {"agent_id": agent_id, "history": []},
        }

    # /agente — info del agente activo
    if text == "/agente":
        return {
            "response": f"Agente activo: <b>{agent_id}</b>",
            "state":    state,
        }

    # Mensaje vacío o solo espacios
    if not text:
        return {"response": "Escríbeme algo para comenzar. 😊", "state": state}

    # Todo lo demás → chat_agent_run
    runner = _get_runner()
    result = runner.run(
        "vertical_chat_agents/chat_agent_run",
        {
            "agent_id": agent_id,
            "message":  text,
            "history":  history,
            "dry_run":  False,
        },
        source="internos",
    )

    if not result.get("ok"):
        return {
            "response": f"⚠️ {result.get('error', 'Error desconocido')}",
            "state":    state,
        }

    data        = result["data"]
    response    = data.get("response", "")
    action      = data.get("action", "reply")
    new_history = data.get("history") or history
    new_state   = {"agent_id": agent_id, "history": new_history}

    # Sufijos por acción
    if action == "capture_lead":
        response += (
            "\n\n📋 <i>Para darte seguimiento, ¿me compartes tu nombre, "
            "correo y teléfono?</i>"
        )
    elif action == "escalate_human":
        response += "\n\n👤 <i>Un asesor de nuestro equipo se pondrá en contacto contigo pronto.</i>"
        new_state["history"] = []  # limpia historial tras derivar
    elif action == "end_conversation":
        new_state["history"] = []  # limpia historial al cerrar

    return {"response": response, "state": new_state}
