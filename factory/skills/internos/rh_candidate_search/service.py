"""Service for rh_candidate_search - filter-based candidate search."""

from __future__ import annotations

from factory.engine import SupabaseClient


class RhCandidateSearchService:

    def ejecutar(self, context: dict) -> dict:
        limite = context.get("limite", 50)
        if not isinstance(limite, int) or limite < 1:
            return {"ok": False, "error": "limite debe ser entero positivo"}

        filters = {}
        for campo in ("vacante_id", "estado", "canal", "empresa_id"):
            if context.get(campo):
                filters[campo] = context[campo]

        if not filters:
            return {"ok": False, "error": "se requiere al menos un filtro: vacante_id, estado, canal o empresa_id"}

        db = SupabaseClient(context)

        result = db.rest_select(
            "candidatos",
            filters=filters,
            select="id,nombre,telefono,email,estado,canal,canal_user_id,vacante_id,created_at",
            limit=limite,
            order="created_at.desc",
        )
        if not result.get("ok"):
            return result

        candidatos = result.get("data") or []

        # Filtro por nombre (ilike no disponible en rest_select simple — filtro en memoria)
        nombre_filtro = (context.get("nombre") or "").lower().strip()
        if nombre_filtro:
            candidatos = [
                c for c in candidatos
                if nombre_filtro in (c.get("nombre") or "").lower()
            ]

        return {
            "ok": True,
            "data": {
                "candidatos": candidatos,
                "total":      len(candidatos),
                "filtros":    filters,
            },
        }
