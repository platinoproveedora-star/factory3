"""Estoiko Lab bot - demo de chat agents con IA para clientes."""
from __future__ import annotations

import os
from pathlib import Path


_BASE = Path(__file__).parent.parent.parent.parent
_DEFAULT_AGENT = os.getenv("ESTOIKOLAB_DEFAULT_AGENT", "AGT-001")

_WELCOME = (
    "Hola, soy <b>Aria Estoiko</b>.\n\n"
    "Puedo ayudarte a imaginar y vender agentes de IA para empresas: "
    "agentes que atienden clientes, responden preguntas, capturan leads, "
    "agendan citas y derivan a un humano cuando el prospecto esta listo.\n\n"
    "Prueba escribiendo algo como:\n"
    "<i>Tengo una agencia de marketing y quiero vender agentes a mis clientes</i>\n"
    "o\n"
    "<i>Tengo una clinica/inmobiliaria/restaurante y quiero automatizar mensajes</i>\n\n"
    "<b>Comandos:</b>\n"
    "/nuevo - reiniciar conversacion\n"
    "/agente - ver agente activo"
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
    message = update.get("message", {})
    text = (message.get("text") or "").strip()
    agent_id = state.get("agent_id", _DEFAULT_AGENT)
    history = state.get("history") or []

    if text in ("/start", "/inicio"):
        return {
            "response": _WELCOME,
            "state": {"agent_id": agent_id, "history": []},
        }

    if text == "/nuevo":
        return {
            "response": (
                "Conversacion reiniciada. Cuentame que negocio quieres convertir "
                "en un demo de agente IA."
            ),
            "state": {"agent_id": agent_id, "history": []},
        }

    if text == "/agente":
        return {
            "response": f"Agente activo: <b>{agent_id}</b> - Aria Estoiko",
            "state": state,
        }

    if not text:
        return {"response": "Escribeme una idea de negocio y armamos el agente.", "state": state}

    runner = _get_runner()
    result = runner.run(
        "vertical_chat_agents/chat_agent_conversation_orchestrator",
        {
            "agent_id": agent_id,
            "message": text,
            "history": history,
            "chat_id": message.get("chat", {}).get("id"),
            "company_id": "EMP_ESTOIKOLAB",
            "canal": "telegram",
            "lead_dry_run": True,
            "dry_run": False,
        },
        source="internos",
    )

    if not result.get("ok"):
        return {
            "response": f"Error: {result.get('error', 'Error desconocido')}",
            "state": state,
        }

    orchestration = result["data"]
    data = orchestration.get("runtime", {})
    evaluation = orchestration.get("evaluation") or {}
    response = data.get("response", "")
    action = data.get("action", "reply")
    new_history = data.get("history") or history
    new_state = {"agent_id": agent_id, "history": new_history}

    if evaluation and not evaluation.get("passed", True):
        response = (
            "Te entiendo. Prefiero aterrizarlo bien y sin sonar generica. "
            "Cuentame en una frase que tipo de negocio quieres automatizar y que resultado buscas."
        )

    if action == "capture_lead":
        response += (
            "\n\nPara preparar una demo enfocada en tu caso, comparteme: "
            "nombre, empresa, telefono o email, y que tipo de negocio quieres automatizar."
        )
    elif action == "escalate_human":
        response += "\n\nUn asesor de Estoiko Lab puede tomar este caso y convertirlo en propuesta."
        new_state["history"] = []
    elif action == "end_conversation":
        new_state["history"] = []

    return {"response": response, "state": new_state}
