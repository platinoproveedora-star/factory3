"""Service for meta_task_enqueue — encola tareas en factory_tasks."""
from __future__ import annotations

from factory.engine import SupabaseClient


class MetaTaskEnqueueService:

    def ejecutar(self, context: dict) -> dict:
        # Acepta tarea única o lista de tareas
        tareas_raw = context.get("tareas")
        if tareas_raw is None:
            # Modo tarea única: skill_name + context en el mismo context
            skill_name = (context.get("skill_name") or "").strip()
            if not skill_name:
                return {"ok": False, "error": "skill_name o tareas requerido"}
            tareas_raw = [context]

        if not isinstance(tareas_raw, list):
            tareas_raw = [tareas_raw]

        if context.get("dry_run", False):
            return {"ok": True, "message": "dry_run", "data": {"tareas": len(tareas_raw)}}

        db          = SupabaseClient(context)
        encoladas   = []
        errores     = []
        siguiente   = self._siguiente_numero(db)

        for i, tarea in enumerate(tareas_raw):
            skill_name   = (tarea.get("skill_name") or "").strip()
            if not skill_name:
                errores.append(f"tarea {i}: skill_name requerido")
                continue

            task_id = f"TASK-{siguiente + i:04d}"
            row = {
                "task_id":        task_id,
                "empresa_id":     tarea.get("empresa_id") or context.get("empresa_id"),
                "skill_name":     skill_name,
                "skill_source":   tarea.get("skill_source", "internos"),
                "context":        tarea.get("context", {}),
                "prioridad":      int(tarea.get("prioridad", 5)),
                "parent_task_id": tarea.get("parent_task_id") or context.get("parent_task_id"),
                "generated_by":   tarea.get("generated_by") or context.get("generated_by"),
                "created_by":     tarea.get("created_by") or context.get("created_by", "human"),
                "status":         "pendiente",
            }
            r = db.rest_insert("factory_tasks", row)
            if r.get("ok"):
                encoladas.append(task_id)
            else:
                errores.append(f"{task_id}: {r.get('error')}")

        return {
            "ok":     True,
            "message": f"{len(encoladas)} tareas encoladas",
            "data": {
                "encoladas": encoladas,
                "errores":   errores,
            },
        }

    def _siguiente_numero(self, db: SupabaseClient) -> int:
        r = db.rest_select("factory_tasks", select="task_id", order="created_at.desc", limit=1)
        rows = (r.get("data") or []) if r.get("ok") else []
        if not rows:
            return 1
        last = rows[0].get("task_id", "TASK-0000")
        try:
            return int(last.split("-")[-1]) + 1
        except (ValueError, IndexError):
            return 1
