"""Service for rh_candidate_ranking - ranks candidates by score for a vacancy."""

from __future__ import annotations

from factory.engine import SupabaseClient

_EXCLUIR_ESTADOS = {"rechazado", "duplicado", "no_apto"}


class RhCandidateRankingService:

    def ejecutar(self, context: dict) -> dict:
        vacante_id = context.get("vacante_id", "").strip()
        if not vacante_id:
            return {"ok": False, "error": "vacante_id es requerido"}

        limite = context.get("limite", 20)
        if not isinstance(limite, int) or limite < 1:
            return {"ok": False, "error": "limite debe ser entero positivo"}

        db = SupabaseClient(context)

        candidatos = db.rest_select(
            "candidatos",
            filters={"vacante_id": vacante_id},
            select="id,nombre,telefono,email,estado,canal,created_at",
        )
        if not candidatos.get("ok"):
            return candidatos

        todos = candidatos.get("data") or []
        elegibles = [c for c in todos if c.get("estado") not in _EXCLUIR_ESTADOS]
        if not elegibles:
            return {"ok": True, "data": {"vacante_id": vacante_id, "ranking": [], "total": 0}}

        ids = [c["id"] for c in elegibles]
        scores_result = db.rest_select(
            "scores",
            filters={"vacante_id": vacante_id},
            select="candidato_id,score_total,pasa_knockout,detalle",
        )
        if not scores_result.get("ok"):
            return scores_result

        score_map = {
            s["candidato_id"]: s
            for s in (scores_result.get("data") or [])
            if s["candidato_id"] in ids
        }

        ranking = []
        for c in elegibles:
            score_data = score_map.get(c["id"], {})
            ranking.append({
                "posicion":      0,
                "candidato_id":  c["id"],
                "nombre":        c.get("nombre") or "Sin nombre",
                "estado":        c.get("estado"),
                "canal":         c.get("canal"),
                "score_total":   score_data.get("score_total"),
                "pasa_knockout": score_data.get("pasa_knockout"),
                "resumen":       (score_data.get("detalle") or {}).get("resumen"),
            })

        ranking.sort(key=lambda x: (x["score_total"] is None, -(x["score_total"] or 0)))
        for i, item in enumerate(ranking[:limite], start=1):
            item["posicion"] = i

        return {
            "ok": True,
            "data": {
                "vacante_id": vacante_id,
                "ranking":    ranking[:limite],
                "total":      len(ranking),
            },
        }
