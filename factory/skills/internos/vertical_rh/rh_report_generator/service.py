"""Service for rh_report_generator - pipeline, scores and conversion reports."""

from __future__ import annotations

from factory.engine import SupabaseClient

_TIPOS = {"pipeline", "scores", "conversion"}


class RhReportGeneratorService:

    def ejecutar(self, context: dict) -> dict:
        tipo       = context.get("tipo", "pipeline").strip()
        vacante_id = context.get("vacante_id", "").strip()
        empresa_id = context.get("empresa_id", "").strip()

        if tipo not in _TIPOS:
            return {"ok": False, "error": f"tipo invalido — validos: {', '.join(_TIPOS)}"}
        if not vacante_id and not empresa_id:
            return {"ok": False, "error": "se requiere vacante_id o empresa_id"}

        db = SupabaseClient(context)

        if tipo == "pipeline":
            return self._reporte_pipeline(db, vacante_id, empresa_id)
        if tipo == "scores":
            return self._reporte_scores(db, vacante_id, empresa_id)
        if tipo == "conversion":
            return self._reporte_conversion(db, vacante_id, empresa_id)

    def _reporte_pipeline(self, db: SupabaseClient, vacante_id: str, empresa_id: str) -> dict:
        filters = {}
        if vacante_id:
            filters["vacante_id"] = vacante_id

        candidatos_r = db.rest_select("candidatos", filters=filters, select="id,estado,canal,vacante_id,created_at")
        if not candidatos_r.get("ok"):
            return candidatos_r

        candidatos = candidatos_r.get("data") or []

        conteo: dict[str, int] = {}
        por_canal: dict[str, int] = {}
        for c in candidatos:
            estado = c.get("estado", "desconocido")
            conteo[estado] = conteo.get(estado, 0) + 1
            canal = c.get("canal", "desconocido")
            por_canal[canal] = por_canal.get(canal, 0) + 1

        return {
            "ok": True,
            "data": {
                "tipo":          "pipeline",
                "vacante_id":    vacante_id or None,
                "empresa_id":    empresa_id or None,
                "total":         len(candidatos),
                "por_estado":    conteo,
                "por_canal":     por_canal,
            },
        }

    def _reporte_scores(self, db: SupabaseClient, vacante_id: str, empresa_id: str) -> dict:
        filters = {}
        if vacante_id:
            filters["vacante_id"] = vacante_id

        scores_r = db.rest_select("scores", filters=filters, select="score_total,pasa_knockout,candidato_id")
        if not scores_r.get("ok"):
            return scores_r

        scores = scores_r.get("data") or []
        if not scores:
            return {"ok": True, "data": {"tipo": "scores", "total": 0, "promedio": None, "pasan_knockout": 0}}

        totales    = [s["score_total"] for s in scores if s.get("score_total") is not None]
        promedio   = round(sum(totales) / len(totales), 1) if totales else None
        alto       = sum(1 for s in totales if s >= 75)
        medio      = sum(1 for s in totales if 50 <= s < 75)
        bajo       = sum(1 for s in totales if s < 50)
        knockout   = sum(1 for s in scores if s.get("pasa_knockout"))

        return {
            "ok": True,
            "data": {
                "tipo":           "scores",
                "vacante_id":     vacante_id or None,
                "total_scores":   len(scores),
                "promedio":       promedio,
                "score_alto":     alto,
                "score_medio":    medio,
                "score_bajo":     bajo,
                "pasan_knockout": knockout,
            },
        }

    def _reporte_conversion(self, db: SupabaseClient, vacante_id: str, empresa_id: str) -> dict:
        pipeline_r, candidatos_r = (
            db.rest_select("pipeline",   filters={"vacante_id": vacante_id} if vacante_id else {}),
            db.rest_select("candidatos", filters={"vacante_id": vacante_id} if vacante_id else {}, select="id,estado"),
        )

        pipeline   = pipeline_r.get("data") or [] if pipeline_r.get("ok") else []
        candidatos = candidatos_r.get("data") or [] if candidatos_r.get("ok") else []

        total      = len(candidatos)
        aptos      = sum(1 for c in candidatos if c.get("estado") in {"apto", "listo_entrevista", "entrevistado", "contratado"})
        contratados = sum(1 for c in candidatos if c.get("estado") == "contratado")
        tasa_aptos = round(aptos / total * 100, 1) if total else 0
        tasa_conv  = round(contratados / total * 100, 1) if total else 0

        return {
            "ok": True,
            "data": {
                "tipo":           "conversion",
                "vacante_id":     vacante_id or None,
                "total_candidatos": total,
                "aptos":          aptos,
                "contratados":    contratados,
                "tasa_aptos_pct": tasa_aptos,
                "tasa_conversion_pct": tasa_conv,
            },
        }
