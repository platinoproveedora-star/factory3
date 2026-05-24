"""Conceptual demo builder for chat agents."""
from __future__ import annotations


class ChatAgentDemoBuilderService:
    def ejecutar(self, context: dict) -> dict:
        business = (context.get("business_type") or context.get("industry") or "negocio").strip()
        goal = (context.get("goal") or "captar y calificar prospectos").strip()
        brand = (context.get("brand") or context.get("client_name") or "el cliente").strip()
        agent_name = (context.get("agent_name") or f"Asesor IA {brand}").strip()
        flow = [
            "Saluda con calidez y pregunta que necesita el visitante.",
            f"Identifica si busca informacion, cotizacion, cita o hablar con {brand}.",
            f"Responde preguntas clave del {business} con informacion aprobada.",
            "Detecta interes real y pide datos de contacto.",
            "Resume la necesidad y deriva al equipo cuando el lead esta listo."
        ]
        demo = {
            "agent_name": agent_name,
            "business_type": business,
            "objective": goal,
            "flow": flow,
            "questions": [
                "Que servicio o solucion estas buscando?",
                "Para cuando lo necesitas?",
                "Como prefieres que te contactemos?",
                "Me compartes tu nombre y telefono?"
            ],
            "captures": ["nombre", "telefono", "email", "necesidad", "urgencia"],
            "welcome_message": (
                f"Hola, soy {agent_name}. Te ayudo a resolver dudas y a encontrar la mejor opcion "
                f"para {goal}. Que te gustaria lograr?"
            )
        }
        return {"ok": True, "data": demo}
