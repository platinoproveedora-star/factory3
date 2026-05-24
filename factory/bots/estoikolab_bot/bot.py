"""Estoiko Lab bot - demo de chat agents con IA para clientes."""
from __future__ import annotations

import os
from pathlib import Path


_BASE = Path(__file__).parent.parent.parent.parent
_DEFAULT_AGENT = os.getenv("ESTOIKOLAB_DEFAULT_AGENT", "AGT-001")
_COMPANY_ID = "EMP_ESTOIKOLAB"

_CONTACT_PROMPT = (
    "Hola, soy <b>Aria Estoiko</b>. Para atenderte bien y guardar tu solicitud, "
    "primero comparteme por favor:\n\n"
    "1. Nombre\n"
    "2. Telefono\n"
    "3. Email\n\n"
    "Despues seguimos con el demo o la consulta."
)

_WELCOME = (
    "Hola, soy <b>Aria Estoiko</b>.\n\n"
    "Te ayudo a crear agentes de IA para empresas: atencion, ventas, FAQs, "
    "captura de leads y demos para tus clientes.\n\n"
    "Para empezar, comparteme nombre, telefono y email.\n\n"
    "Comandos: /hotel para probar el agente de recepcion y ventas de hoteles."
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


def _missing_label(fields: list[str]) -> str:
    labels = {"nombre": "nombre", "telefono": "telefono", "email": "email"}
    return ", ".join(labels.get(field, field) for field in fields)


def _append_history(history: list, role: str, content: str) -> list:
    new_history = list(history)
    if content:
        new_history.append({"role": role, "content": content})
    return new_history


def handle_update(update: dict, state: dict) -> dict:
    message = update.get("message", {})
    text = (message.get("text") or "").strip()
    chat_id = message.get("chat", {}).get("id")
    agent_id = state.get("agent_id", _DEFAULT_AGENT)
    history = state.get("history") or []

    if text in ("/start", "/inicio"):
        return {
            "response": _WELCOME,
            "state": {"agent_id": agent_id, "history": [], "contact_requested": True},
        }

    if text == "/nuevo":
        return {
            "response": _CONTACT_PROMPT,
            "state": {"agent_id": agent_id, "history": [], "contact_requested": True},
        }

    if text == "/agente":
        return {
            "response": f"Agente activo: <b>{agent_id}</b> - Aria Estoiko",
            "state": state,
        }

    if text == "/hotel":
        hotel_agent = "AGT-HOTEL-001"
        return {
            "response": (
                "Activamos el demo de hotel: <b>Sofia Concierge</b>.\n\n"
                "Primero comparteme nombre, telefono y email para guardar tu solicitud. "
                "Despues podras probarlo como si fueras huesped de un hotel boutique."
            ),
            "state": {"agent_id": hotel_agent, "history": [], "contact_requested": True},
        }

    if not text:
        return {"response": _CONTACT_PROMPT, "state": state}

    runner = _get_runner()

    if not state.get("lead_id"):
        lead_result = runner.run(
            "vertical_chat_agents/chat_agent_lead_capture",
            {
                "message": text,
                "history": history,
                "chat_id": chat_id,
                "company_id": _COMPANY_ID,
                "canal": "telegram",
                "required_fields": ["nombre", "telefono", "email"],
                "force_new": True,
                "dry_run": False,
            },
            source="internos",
        )
        new_history = _append_history(history, "user", text)
        if not lead_result.get("ok"):
            return {
                "response": "No pude guardar tus datos todavia. Puedes mandarme nombre, telefono y email otra vez?",
                "state": {"agent_id": agent_id, "history": new_history, "contact_requested": True},
            }
        lead_data = lead_result.get("data") or {}
        if not lead_data.get("saved"):
            missing = lead_data.get("missing_fields") or ["nombre", "telefono", "email"]
            response = f"Gracias. Me falta tu {_missing_label(missing)} para guardar tu solicitud y continuar."
            return {
                "response": response,
                "state": {"agent_id": agent_id, "history": new_history, "contact_requested": True},
            }
        lead = lead_data.get("lead") or {}
        contact = lead_data.get("contact") or {}
        lead_id = lead.get("lead_id")
        folio = lead.get("folio")
        response = (
            f"Gracias, {contact.get('nombre') or 'listo'}. Ya guarde tu solicitud"
            f"{f' con folio {folio}' if folio else ''}.\n\n"
            "Ahora si, cuentame que agente quieres probar o que negocio quieres automatizar."
        )
        return {
            "response": response,
            "state": {
                "agent_id": agent_id,
                "history": new_history,
                "contact_requested": True,
                "contact_captured": True,
                "lead_id": lead_id,
                "lead_folio": folio,
                "contact": contact,
            },
        }

    result = runner.run(
        "vertical_chat_agents/chat_agent_conversation_orchestrator",
        {
            "agent_id": agent_id,
            "message": text,
            "history": history,
            "chat_id": chat_id,
            "company_id": _COMPANY_ID,
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
    new_state = {
        **state,
        "agent_id": agent_id,
        "history": new_history,
    }

    if evaluation and not evaluation.get("passed", True):
        response = (
            "Te entiendo. Prefiero aterrizarlo bien y sin sonar generica. "
            "Cuentame en una frase que tipo de negocio quieres automatizar y que resultado buscas."
        )

    if action == "capture_lead":
        response += "\n\nYa tengo tus datos iniciales. Si quieres, ahora dime que tipo de demo preparamos."
    elif action == "escalate_human":
        response += "\n\nUn asesor de Estoiko Lab puede tomar este caso y convertirlo en propuesta."
    elif action == "end_conversation":
        new_state["history"] = []

    return {"response": response, "state": new_state}
