"""Service for rh_pipeline_manager - manages candidate pipeline stages."""

from __future__ import annotations

from factory.engine import SupabaseClient

_ETAPAS = {
    "incompleto", "duplicado", "no_apto", "apto",
    "listo_entrevista", "entrevistado", "contratado", "rechazado",
}


class RhPipelineManagerService:

    def ejecutar(self, context: dict) -> dict:
        candidato_id = context.get("candidato_id", "").strip()
        vacante_id   = context.get("vacante_id", "").strip()
        etapa        = context.get("etapa", "").strip()
        notas        = context.get("notas", "")

        if not candidato_id:
            return {"ok": False, "error": "candidato_id es requerido"}
        if not vacante_id:
            return {"ok": False, "error": "vacante_id es requerido"}
        if not etapa or etapa not in _ETAPAS:
            return {"ok": False, "error": f"etapa invalida — validas: {', '.join(sorted(_ETAPAS))}"}

        db = SupabaseClient(context)

        # Buscar registro existente en pipeline
        existing = db.rest_select(
            "pipeline",
            filters={"candidato_id": candidato_id, "vacante_id": vacante_id},
            select="id,etapa",
            limit=1,
        )
        if not existing.get("ok"):
            return existing

        rows = existing.get("data") or []
        etapa_anterior = rows[0]["etapa"] if rows else None

        if rows:
            pipeline_id = rows[0]["id"]
            update_vals = {"etapa": etapa}
            if notas:
                update_vals["notas"] = notas
            result = db.rest_update("pipeline", values=update_vals, filters={"id": pipeline_id})
        else:
            insert_vals = {"candidato_id": candidato_id, "vacante_id": vacante_id, "etapa": etapa}
            if notas:
                insert_vals["notas"] = notas
            result = db.rest_insert("pipeline", insert_vals)

        if not result.get("ok"):
            return result

        # Actualizar estado en candidatos
        db.rest_update("candidatos", values={"estado": etapa}, filters={"id": candidato_id})

        # Registrar en historial
        db.rest_insert("eventos_historial", {
            "candidato_id": candidato_id,
            "tipo_evento":  "pipeline_cambiado",
            "datos": {
                "etapa_anterior": etapa_anterior,
                "etapa_nueva":    etapa,
                "vacante_id":     vacante_id,
                "notas":          notas or None,
            },
        })

        return {
            "ok": True,
            "message": f"candidato movido a '{etapa}'",
            "data": {
                "candidato_id":  candidato_id,
                "etapa_anterior": etapa_anterior,
                "etapa_nueva":    etapa,
            },
        }
