"""KPIs generales del sistema RH."""
from __future__ import annotations
import os
from factory.engine import SupabaseClient

_EMPRESA_ID = os.getenv("RH_EMPRESA_ID", "rh_empresa_1")


class RhStatsService:

    def ejecutar(self, context: dict) -> dict:
        empresa_id = context.get("empresa_id", _EMPRESA_ID)
        db = SupabaseClient(context)

        vacantes    = self._count(db, "vacantes",   f"empresa_id=eq.{empresa_id}")
        activas     = self._count(db, "vacantes",   f"empresa_id=eq.{empresa_id}&estado=eq.activa")
        seeds_v     = self._count(db, "vacantes",   f"empresa_id=eq.{empresa_id}&tipo=eq.seed")
        candidatos  = self._count(db, "candidatos", f"vacante_id=in.(select id from vacantes where empresa_id='{empresa_id}')")
        aptos       = self._count(db, "candidatos", f"estado=eq.apto")
        scores_rows = db.rest_select("scores", select="score_total,pasa_knockout", limit=1000)
        scores      = (scores_rows.get("data") or []) if scores_rows.get("ok") else []
        score_prom  = round(sum(s.get("score_total", 0) for s in scores) / len(scores), 1) if scores else 0
        pasan_ko    = sum(1 for s in scores if s.get("pasa_knockout"))

        seeds_labels = db.rest_select("test_seeds", select="seed_label", limit=1000)
        labels = set()
        for r in (seeds_labels.get("data") or []) if seeds_labels.get("ok") else []:
            labels.add(r.get("seed_label", ""))
        seeds_total = len(labels)

        return {
            "ok": True,
            "data": {
                "empresa_id":      empresa_id,
                "vacantes_total":  vacantes,
                "vacantes_activas": activas,
                "vacantes_seed":   seeds_v,
                "candidatos_total": candidatos,
                "candidatos_aptos": aptos,
                "score_promedio":  score_prom,
                "pasan_knockout":  pasan_ko,
                "seeds_total":     seeds_total,
            },
        }

    def _count(self, db, tabla: str, filters: str) -> int:
        r = db.rest_select(tabla, filters=self._parse(filters), select="id", limit=1)
        if not r.get("ok"):
            return 0
        return len(r.get("data") or [])

    def _parse(self, filters: str) -> dict:
        result = {}
        for part in filters.split("&"):
            if "=" in part:
                k, v = part.split("=", 1)
                result[k] = v
        return result
