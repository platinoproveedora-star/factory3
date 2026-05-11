"""Service for meta_task_status — snapshot de la cola factory_tasks."""
from __future__ import annotations

from factory.engine import SupabaseClient


class MetaTaskStatusService:

    def ejecutar(self, context: dict) -> dict:
        empresa_id = context.get("empresa_id")
        limit      = int(context.get("limit", 100))
        status     = context.get("status")

        db      = SupabaseClient(context)
        filters: dict = {}
        if empresa_id:
            filters["empresa_id"] = empresa_id
        if status:
            filters["status"] = status

        r = db.rest_select(
            "factory_tasks",
            filters=filters,
            select="task_id,skill_name,skill_source,status,prioridad,empresa_id,created_by,parent_task_id,generated_by,latencia_ms,costo_tokens,error_msg,created_at,started_at,finished_at",
            order="created_at.desc",
            limit=limit,
        )
        tareas = (r.get("data") or []) if r.get("ok") else []

        conteo: dict[str, int] = {}
        for t in tareas:
            s = t.get("status", "?")
            conteo[s] = conteo.get(s, 0) + 1

        return {
            "ok": True,
            "data": {
                "tareas":  tareas,
                "conteo":  conteo,
                "total":   len(tareas),
            },
        }
