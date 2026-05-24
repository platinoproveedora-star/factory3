"""System prompt builder for chat agents."""
from __future__ import annotations


class ChatAgentPromptBuilderService:
    def ejecutar(self, context: dict) -> dict:
        agent = context.get("agent") or {}
        attitude = context.get("attitude") or {}
        guardrails = context.get("guardrails") or {}
        knowledge = (context.get("knowledge") or "").strip()
        allowed_actions = agent.get("allowed_actions") or ["reply", "capture_lead", "escalate_human", "end_conversation"]

        lines = [
            attitude.get("identity") or f"Eres {agent.get('name', 'un asesor virtual')}.",
            f"OBJETIVO: {agent.get('objective', 'ayudar al usuario')}",
            f"TONO: {attitude.get('tone') or agent.get('tone', 'humano, calido y profesional')}",
            "",
            "ESTILO DE CONVERSACION:"
        ]
        lines.extend(f"- {x}" for x in attitude.get("conversation_style", []))
        if attitude.get("sales_attitude"):
            lines.append("")
            lines.append("ACTITUD COMERCIAL:")
            lines.extend(f"- {x}" for x in attitude.get("sales_attitude", []))
        if agent.get("rules"):
            lines.append("")
            lines.append("REGLAS DEL AGENTE:")
            lines.extend(f"- {x}" for x in agent.get("rules", []))
        if guardrails.get("rules"):
            lines.append("")
            lines.append("GUARDRAILS:")
            lines.extend(f"- {x}" for x in guardrails.get("rules", []))
        if knowledge:
            lines.append("")
            lines.append("CONOCIMIENTO BASE:")
            lines.append(knowledge)
        lines.append("")
        lines.append("ACCIONES:")
        action_docs = {
            "reply": "[ACCION:reply] respuesta normal",
            "capture_lead": "[ACCION:capture_lead] cuando hay interes real o pide demo/cotizacion",
            "escalate_human": "[ACCION:escalate_human] cuando necesita humano, precio formal o integracion especifica",
            "end_conversation": "[ACCION:end_conversation] cuando la conversacion termina naturalmente"
        }
        for action in allowed_actions:
            if action in action_docs:
                lines.append(f"- {action_docs[action]}")
        lines.append("La etiqueta de accion debe ir al final de cada respuesta.")
        return {"ok": True, "data": {"system_prompt": "\n".join(lines), "allowed_actions": allowed_actions}}
