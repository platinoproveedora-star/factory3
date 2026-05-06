"""Service for rh_candidate_history - full candidate timeline."""

from __future__ import annotations

from factory.engine import SupabaseClient


class RhCandidateHistoryService:

    def ejecutar(self, context: dict) -> dict:
        candidato_id = context.get("candidato_id", "").strip()
        if not candidato_id:
            return {"ok": False, "error": "candidato_id es requerido"}

        db = SupabaseClient(context)

        perfil_r = db.rest_select("candidatos", filters={"id": candidato_id}, limit=1)
        if not perfil_r.get("ok"):
            return perfil_r
        rows = perfil_r.get("data") or []
        if not rows:
            return {"ok": False, "error": f"candidato no encontrado: {candidato_id}"}
        perfil = rows[0]

        respuestas_r  = db.rest_select("respuestas",       filters={"candidato_id": candidato_id}, order="orden.asc")
        scores_r      = db.rest_select("scores",           filters={"candidato_id": candidato_id}, order="created_at.desc")
        pipeline_r    = db.rest_select("pipeline",         filters={"candidato_id": candidato_id}, order="created_at.asc")
        eventos_r     = db.rest_select("eventos_historial", filters={"candidato_id": candidato_id}, order="created_at.asc")
        alertas_r     = db.rest_select("alertas",          filters={"candidato_id": candidato_id}, order="created_at.desc")

        return {
            "ok": True,
            "data": {
                "candidato_id": candidato_id,
                "perfil":       perfil,
                "respuestas":   respuestas_r.get("data") or [],
                "scores":       scores_r.get("data") or [],
                "pipeline":     pipeline_r.get("data") or [],
                "eventos":      eventos_r.get("data") or [],
                "alertas":      alertas_r.get("data") or [],
            },
        }
