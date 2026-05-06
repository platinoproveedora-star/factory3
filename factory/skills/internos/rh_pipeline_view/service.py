"""Vista de pipeline RH agrupada por etapa."""
from __future__ import annotations
import os
from factory.engine import SupabaseClient

_EMPRESA_ID = os.getenv("RH_EMPRESA_ID", "rh_empresa_1")
_ETAPAS     = ["nuevo", "apto", "listo_entrevista", "entrevistado", "rechazado", "no_apto", "contratado"]


class RhPipelineViewService:

    def ejecutar(self, context: dict) -> dict:
        empresa_id  = context.get("empresa_id", _EMPRESA_ID)
        vacante_id  = context.get("vacante_id", "")
        limit       = min(int(context.get("limit", 500)), 1000)

        db = SupabaseClient(context)

        pipeline_filters = {}
        if vacante_id:
            pipeline_filters["vacante_id"] = vacante_id

        p_r = db.rest_select("pipeline", filters=pipeline_filters,
                             select="candidato_id,vacante_id,etapa,notas,created_at",
                             limit=limit)
        pipeline = (p_r.get("data") or []) if p_r.get("ok") else []

        c_r = db.rest_select("candidatos", filters={},
                             select="id,folio,nombre,telefono,estado,vacante_id",
                             limit=limit)
        cands = {c["id"]: c for c in ((c_r.get("data") or []) if c_r.get("ok") else [])}

        v_r = db.rest_select("vacantes", filters={"empresa_id": empresa_id},
                             select="id,folio,titulo", limit=200)
        vacs = {v["id"]: v for v in ((v_r.get("data") or []) if v_r.get("ok") else [])}

        by_etapa: dict[str, list] = {e: [] for e in _ETAPAS}
        totales:  dict[str, int]  = {e: 0  for e in _ETAPAS}

        for p in pipeline:
            etapa = p.get("etapa", "nuevo")
            if etapa not in by_etapa:
                by_etapa[etapa] = []
            cand = cands.get(p.get("candidato_id"), {})
            vac  = vacs.get(p.get("vacante_id"), {})
            by_etapa[etapa].append({
                "candidato_folio":  cand.get("folio", "?"),
                "candidato_nombre": cand.get("nombre", "?"),
                "vacante_folio":    vac.get("folio", "?"),
                "vacante_titulo":   vac.get("titulo", "?"),
                "notas":            p.get("notas", ""),
            })
            totales[etapa] = totales.get(etapa, 0) + 1

        return {
            "ok": True,
            "data": {
                "by_etapa": by_etapa,
                "totales":  totales,
                "etapas":   _ETAPAS,
                "total":    len(pipeline),
            },
        }
