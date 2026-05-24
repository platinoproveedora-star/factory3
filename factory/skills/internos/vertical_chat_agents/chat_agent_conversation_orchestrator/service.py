"""Orchestrates chat agent runtime, response evaluation and lead capture."""
from __future__ import annotations
from pathlib import Path


_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent


class ChatAgentConversationOrchestratorService:
    def ejecutar(self, context: dict) -> dict:
        from factory.engine import SkillLoader, SkillRunner
        loader = SkillLoader(internal_root=_ROOT / "factory" / "skills" / "internos", external_root=_ROOT / "factory" / "skills" / "externos")
        runner = SkillRunner(loader)
        run_r = runner.run("vertical_chat_agents/chat_agent_run", {
            "agent_id": context.get("agent_id", "AGT-001"),
            "message": context.get("message", ""),
            "history": context.get("history") or [],
            "dry_run": context.get("dry_run", False)
        }, source="internos")
        if not run_r.get("ok"):
            return run_r
        data = run_r.get("data") or {}
        eval_r = runner.run("vertical_chat_agents/chat_agent_response_evaluator", {
            "response": data.get("response", ""),
            "min_score": context.get("min_response_score", 70)
        }, source="internos")
        lead_r = None
        if data.get("action") == "capture_lead" and context.get("capture_lead", True):
            lead_r = runner.run("vertical_chat_agents/chat_agent_lead_capture", {
                "message": context.get("message", ""),
                "user_id": context.get("user_id") or context.get("chat_id", ""),
                "empresa_id": context.get("empresa_id") or context.get("company_id") or "EMP_ESTOIKOLAB",
                "canal": context.get("canal", "telegram"),
                "dry_run": context.get("lead_dry_run", True)
            }, source="internos")
        return {"ok": True, "data": {"runtime": data, "evaluation": eval_r.get("data"), "lead_capture": lead_r}}
