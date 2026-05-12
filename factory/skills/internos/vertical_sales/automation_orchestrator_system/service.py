"""Decide siguiente acción post-lead según score e intención. Encola tarea y registra log."""
from __future__ import annotations
import json, os, urllib.request
from datetime import datetime, timezone

_SCHEMA = "sales"


def _decidir(intent: str, score: int, es_nuevo: bool) -> tuple[str, str]:
    if score >= 70:
        return "followup_inmediato", "vertical_sales/ai_followup_system"
    if es_nuevo and score >= 40:
        return "followup_programado", "vertical_sales/ai_followup_system"
    if intent == "queja":
        return "escalar_humano", "vertical_sales/ai_followup_system"
    return "monitorear", "vertical_sales/dashboard_operational_system"


class AutomationOrchestratorService:

    def ejecutar(self, context: dict) -> dict:
        lead_id    = context.get("lead_id", "").strip()
        empresa_id = context.get("empresa_id", "").strip()
        intent     = context.get("intent", "otro").strip()
        score      = int(context.get("score", 0))
        es_nuevo   = bool(context.get("es_nuevo", True))
        dry_run    = context.get("dry_run", True)

        if not lead_id:
            return {"ok": False, "error": "lead_id requerido"}
        if not empresa_id:
            return {"ok": False, "error": "empresa_id requerido"}

        accion, skill_destino = _decidir(intent, score, es_nuevo)

        if dry_run:
            return {"ok": True, "data": {
                "accion":        accion,
                "task_id":       "AUT-DRY",
                "skill_destino": skill_destino,
                "dry_run":       True,
            }}

        url = os.getenv("SUPABASE_URL", "").rstrip("/")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        if not url or not key:
            return {"ok": False, "error": "Faltan SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY"}

        folio = self._next_folio("AUT", url, key)
        self._insert_log({
            "folio":         folio,
            "empresa_id":    empresa_id,
            "lead_id":       lead_id,
            "accion":        accion,
            "skill_destino": skill_destino,
            "estado":        "encolado",
        }, url, key)

        task_id = self._enqueue(skill_destino, {"lead_id": lead_id, "empresa_id": empresa_id, "intent": intent}, empresa_id, url, key)

        return {"ok": True, "data": {
            "accion":        accion,
            "task_id":       task_id or folio,
            "skill_destino": skill_destino,
        }}

    def _enqueue(self, skill_name: str, ctx: dict, empresa_id: str, url: str, key: str) -> str | None:
        try:
            task_id = f"sales_{int(datetime.now(timezone.utc).timestamp())}"
            req = urllib.request.Request(
                f"{url}/rest/v1/factory_tasks",
                data=json.dumps({
                    "task_id":      task_id,
                    "skill_name":   skill_name,
                    "skill_source": "internos",
                    "context":      ctx,
                    "empresa_id":   empresa_id,
                    "estado":       "pendiente",
                    "prioridad":    5,
                }).encode(),
                headers={
                    "apikey":        key,
                    "Authorization": f"Bearer {key}",
                    "Content-Type":  "application/json",
                    "Prefer":        "return=representation",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                rows = json.loads(r.read().decode())
                return rows[0].get("task_id") if rows else task_id
        except Exception:
            return None

    def _next_folio(self, prefix: str, url: str, key: str) -> str:
        try:
            req = urllib.request.Request(
                f"{url}/rest/v1/automation_logs?select=folio&order=created_at.desc&limit=1",
                headers={"apikey": key, "Authorization": f"Bearer {key}", "Accept-Profile": _SCHEMA},
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                rows = json.loads(r.read().decode())
                if rows:
                    return f"{prefix}-{int(rows[0]['folio'].split('-')[-1]) + 1:03d}"
        except Exception:
            pass
        return f"{prefix}-001"

    def _insert_log(self, row: dict, url: str, key: str) -> None:
        try:
            req = urllib.request.Request(
                f"{url}/rest/v1/automation_logs",
                data=json.dumps(row).encode(),
                headers={
                    "apikey":          key,
                    "Authorization":   f"Bearer {key}",
                    "Content-Type":    "application/json",
                    "Content-Profile": _SCHEMA,
                    "Prefer":          "return=representation",
                },
                method="POST",
            )
            urllib.request.urlopen(req, timeout=10)
        except Exception:
            pass
