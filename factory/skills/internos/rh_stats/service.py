"""KPIs generales del sistema RH."""
from __future__ import annotations
import os
from factory.engine import SupabaseClient

_EMPRESA_ID = os.getenv("RH_EMPRESA_ID", "rh_empresa_1")


class RhStatsService:

    def ejecutar(self, context: dict) -> dict:
        empresa_id = context.get("empresa_id", _EMPRESA_ID)
        db = SupabaseClient(context)

        # Vacantes
        v_all = db.rest_select("vacantes", filters={"empresa_id": empresa_id}, select="id,estado,tipo", limit=1000)
        vacantes = (v_all.get("data") or []) if v_all.get("ok") else []
        vacantes_ids = {v["id"] for v in vacantes}
        vacantes_activas = sum(1 for v in vacantes if v.get("estado") == "activa")
        vacantes_seed    = sum(1 for v in vacantes if v.get("tipo") == "seed")

        # Candidatos (filtrados por vacantes de la empresa)
        c_all = db.rest_select("candidatos", filters={}, select="id,estado,vacante_id", limit=2000)
        candidatos = [c for c in ((c_all.get("data") or []) if c_all.get("ok") else [])
                      if c.get("vacante_id") in vacantes_ids]
        candidatos_aptos = sum(1 for c in candidatos if c.get("estado") == "apto")

        # Scores
        cand_ids = {c["id"] for c in candidatos}
        s_all = db.rest_select("scores", filters={}, select="candidato_id,score_total,pasa_knockout", limit=2000)
        scores = [s for s in ((s_all.get("data") or []) if s_all.get("ok") else [])
                  if s.get("candidato_id") in cand_ids]
        score_prom = round(sum(s.get("score_total", 0) for s in scores) / len(scores), 1) if scores else 0
        pasan_ko   = sum(1 for s in scores if s.get("pasa_knockout"))

        # Seeds
        t_all = db.rest_select("test_seeds", filters={"empresa_id": empresa_id}, select="seed_label", limit=1000)
        labels = {r.get("seed_label") for r in ((t_all.get("data") or []) if t_all.get("ok") else [])}

        return {
            "ok": True,
            "data": {
                "empresa_id":       empresa_id,
                "vacantes_total":   len(vacantes),
                "vacantes_activas": vacantes_activas,
                "vacantes_seed":    vacantes_seed,
                "candidatos_total": len(candidatos),
                "candidatos_aptos": candidatos_aptos,
                "score_promedio":   score_prom,
                "pasan_knockout":   pasan_ko,
                "seeds_total":      len(labels),
            },
        }
