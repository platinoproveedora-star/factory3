"""Config builder for company chat agents."""
from __future__ import annotations
import json
import re
from pathlib import Path


_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent


class ChatAgentConfigBuilderService:
    def ejecutar(self, context: dict) -> dict:
        company_id = (context.get("company_id") or "EMP_ESTOIKOLAB").strip()
        agent_id = (context.get("agent_id") or "AGT-001").strip()
        agent_name = (context.get("agent_name") or "Asesor IA").strip()
        client_name = (context.get("client_name") or company_id).strip()
        objective = (context.get("objective") or "atender y calificar prospectos").strip()
        dry_run = context.get("dry_run", True)

        knowledge_name = f"{self._slug(agent_id)}_knowledge.txt"
        config = {
            "agent_id": agent_id,
            "client_name": client_name,
            "name": agent_name,
            "objective": objective,
            "persona": context.get("persona") or f"Soy {agent_name}, asesora virtual de {client_name}.",
            "tone": context.get("tone") or "humano, calido, consultivo y profesional",
            "welcome_message": context.get("welcome_message") or f"Hola, soy {agent_name}. Cuentame que necesitas y te ayudo.",
            "language": context.get("language", "es"),
            "rules": context.get("rules") or [
                "Diagnosticar antes de vender.",
                "Responder con calidez y claridad.",
                "Pedir datos solo cuando exista interes real.",
                "Derivar a humano cuando se requiere precio formal o integracion."
            ],
            "limits": context.get("limits") or [
                "No inventar precios ni promesas.",
                "No pedir datos sensibles.",
                "No fingir ser una persona real."
            ],
            "allowed_actions": context.get("allowed_actions") or ["reply", "capture_lead", "escalate_human", "end_conversation"],
            "lead_fields": context.get("lead_fields") or ["nombre", "empresa", "telefono", "email", "necesidad"],
            "lead_trigger": context.get("lead_trigger") or "el usuario pide demo, cotizacion o seguimiento",
            "escalation_trigger": context.get("escalation_trigger") or "el usuario pide hablar con una persona o requiere propuesta formal",
            "knowledge_file": f"knowledge/{knowledge_name}",
            "max_turns": int(context.get("max_turns", 24)),
            "status": context.get("status", "active")
        }
        knowledge = context.get("knowledge") or self._default_knowledge(client_name, objective)
        files = {
            f"companies/{company_id}/agents/{agent_id}.json": json.dumps(config, indent=2, ensure_ascii=False),
            f"companies/{company_id}/knowledge/{knowledge_name}": knowledge
        }
        if not dry_run:
            for rel, content in files.items():
                path = _ROOT / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
        return {"ok": True, "data": {"config": config, "knowledge": knowledge, "files": files, "dry_run": dry_run}}

    def _slug(self, value: str) -> str:
        return re.sub(r"[^a-z0-9_]+", "_", value.lower()).strip("_") or "agent"

    def _default_knowledge(self, client_name: str, objective: str) -> str:
        return (
            f"EMPRESA: {client_name}\n"
            f"OBJETIVO DEL AGENTE: {objective}\n\n"
            "INSTRUCCIONES:\n"
            "- Entender la necesidad del visitante.\n"
            "- Responder con informacion aprobada.\n"
            "- Capturar datos cuando exista interes real.\n"
            "- Derivar a humano si necesita propuesta formal.\n"
        )
