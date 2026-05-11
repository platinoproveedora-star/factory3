"""Service for meta_task_runner — ejecuta tareas pendientes de factory_tasks."""
from __future__ import annotations

import time
from pathlib import Path

from factory.engine import SkillLoader, SkillRunner, SupabaseClient


class MetaTaskRunnerService:

    def ejecutar(self, context: dict) -> dict:
        batch_size = int(context.get("batch_size", 10))
        empresa_id = context.get("empresa_id")

        db      = SupabaseClient(context)
        tareas  = self._tomar_pendientes(db, batch_size, empresa_id)

        if not tareas:
            return {"ok": True, "message": "sin tareas pendientes", "data": {"procesadas": 0}}

        runner   = self._build_runner()
        resumen  = {"ok": 0, "error": 0, "total": len(tareas)}
        detalles = []

        for tarea in tareas:
            task_id     = tarea["task_id"]
            skill_name  = tarea["skill_name"]
            skill_source = tarea.get("skill_source", "internos")
            ctx         = tarea.get("context") or {}

            self._marcar_corriendo(db, task_id)
            t0 = time.time()

            try:
                src = skill_source
                if src == "meta":
                    src = self._meta_root
                elif src == "eval":
                    src = self._eval_root
                resultado = runner.run(skill_name, ctx, source=src)
            except Exception as e:
                resultado = {"ok": False, "error": str(e)}

            latencia_ms = int((time.time() - t0) * 1000)
            tokens      = self._extraer_tokens(resultado)
            eval_result = self._eval_basico(resultado)

            if resultado.get("ok"):
                resumen["ok"] += 1
                self._marcar_completada(db, task_id, resultado, latencia_ms, tokens, eval_result)
            else:
                resumen["error"] += 1
                self._marcar_error(db, task_id, resultado.get("error", "error desconocido"), latencia_ms, eval_result)

            detalles.append({
                "task_id":    task_id,
                "skill":      skill_name,
                "ok":         resultado.get("ok"),
                "latencia_ms": latencia_ms,
                "tokens":     tokens,
            })

        return {
            "ok":     True,
            "message": f"{resumen['ok']} ok / {resumen['error']} errores de {resumen['total']}",
            "data":   {"resumen": resumen, "detalles": detalles},
        }

    # ── helpers ──────────────────────────────────────────────────────────────

    def _build_runner(self) -> SkillRunner:
        base = Path(__file__).parent.parent.parent.parent.parent  # factory3 root
        skills_dir = base / "factory" / "skills"
        ext = skills_dir / "externos"
        ext.mkdir(parents=True, exist_ok=True)
        loader = SkillLoader(
            internal_root=skills_dir / "internos",
            external_root=ext,
        )
        self._meta_root = str(skills_dir / "meta")
        self._eval_root = str(skills_dir / "eval")
        return SkillRunner(loader)

    def _tomar_pendientes(self, db: SupabaseClient, n: int, empresa_id: str | None) -> list:
        filters: dict = {"status": "pendiente"}
        if empresa_id:
            filters["empresa_id"] = empresa_id
        r = db.rest_select(
            "factory_tasks",
            filters=filters,
            select="*",
            order="prioridad.asc,created_at.asc",
            limit=n,
        )
        return (r.get("data") or []) if r.get("ok") else []

    def _marcar_corriendo(self, db: SupabaseClient, task_id: str) -> None:
        db.rest_update(
            "factory_tasks",
            {"status": "corriendo", "started_at": "now()"},
            {"task_id": task_id},
        )

    def _marcar_completada(
        self, db: SupabaseClient, task_id: str,
        resultado: dict, latencia_ms: int, tokens: int, eval_result: dict,
    ) -> None:
        payload = resultado.copy()
        payload["_eval"] = eval_result
        db.rest_update(
            "factory_tasks",
            {
                "status":       "completada",
                "resultado":    payload,
                "latencia_ms":  latencia_ms,
                "costo_tokens": tokens,
                "finished_at":  "now()",
            },
            {"task_id": task_id},
        )

    def _marcar_error(
        self, db: SupabaseClient, task_id: str,
        error_msg: str, latencia_ms: int, eval_result: dict,
    ) -> None:
        db.rest_update(
            "factory_tasks",
            {
                "status":      "error",
                "error_msg":   error_msg,
                "resultado":   {"_eval": eval_result},
                "latencia_ms": latencia_ms,
                "finished_at": "now()",
            },
            {"task_id": task_id},
        )

    def _extraer_tokens(self, resultado: dict) -> int:
        data = resultado.get("data") or {}
        return int(data.get("tokens_used", 0))

    def _eval_basico(self, resultado: dict) -> dict:
        has_ok    = "ok" in resultado
        is_dict   = isinstance(resultado, dict)
        ok_bool   = isinstance(resultado.get("ok"), bool)
        has_data  = "data" in resultado or "error" in resultado
        valido    = all([has_ok, is_dict, ok_bool, has_data])
        return {
            "valido":   valido,
            "has_ok":   has_ok,
            "ok_bool":  ok_bool,
            "has_data": has_data,
        }
