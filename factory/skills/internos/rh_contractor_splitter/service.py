"""Service for rh_contractor_splitter — divide candidatos calificados por empresa."""

from __future__ import annotations
import os
from collections import defaultdict


class RhContractorSplitterService:

    def ejecutar(self, context: dict) -> dict:
        valido, error = self._validar(context)
        if not valido:
            return {"ok": False, "error": error}

        vacante_id = context.get("vacante_id")
        empresa_ids = context.get("empresa_ids", [])
        cupos = context.get("cupos", {})
        score_minimo = float(context.get("score_minimo", 60.0))
        estado_filtro = context.get("estado", "apto")

        candidatos = self._obtener_candidatos(vacante_id, estado_filtro, score_minimo)
        if not candidatos["ok"]:
            return candidatos

        asignaciones = self._asignar(candidatos["data"], empresa_ids, cupos)

        return {
            "ok": True,
            "data": {
                "total_candidatos": len(candidatos["data"]),
                "asignados": sum(len(v) for v in asignaciones.values()),
                "sin_asignar": len(candidatos["data"]) - sum(len(v) for v in asignaciones.values()),
                "por_empresa": asignaciones,
            },
        }

    def _obtener_candidatos(self, vacante_id: str | None, estado: str, score_min: float) -> dict:
        try:
            from factory.engine import SupabaseClient
            sb = SupabaseClient({})

            filters: dict = {"estado": estado}
            if vacante_id:
                filters["vacante_id"] = vacante_id

            resp      = sb.rest_select("candidatos", filters, select="id,nombre,telefono,email,estado,vacante_id,empresa_id")
            candidatos = resp.get("data") or []

            if score_min > 0 and candidatos:
                ids        = [c["id"] for c in candidatos]
                ids_filter = "in.(" + ",".join(ids) + ")"
                sc_resp    = sb.rest_select("scores", {"candidato_id": ids_filter, "score_total": f"gte.{score_min}"}, select="candidato_id,score_total")
                ids_ok     = {s["candidato_id"] for s in (sc_resp.get("data") or [])}
                candidatos = [c for c in candidatos if c["id"] in ids_ok]

            return {"ok": True, "data": candidatos}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _asignar(self, candidatos: list, empresa_ids: list, cupos: dict) -> dict:
        asignaciones: dict = defaultdict(list)

        if not empresa_ids:
            empresa_ids = list({c.get("empresa_id") for c in candidatos if c.get("empresa_id")})

        contadores = {eid: 0 for eid in empresa_ids}
        idx = 0

        for candidato in candidatos:
            if idx >= len(empresa_ids):
                break
            empresa = empresa_ids[idx % len(empresa_ids)]
            cupo = cupos.get(empresa, 9999)
            if contadores[empresa] >= cupo:
                idx += 1
                if idx >= len(empresa_ids):
                    break
                empresa = empresa_ids[idx % len(empresa_ids)]
            asignaciones[empresa].append(candidato["id"])
            contadores[empresa] += 1

        return dict(asignaciones)

    def _validar(self, context: dict) -> tuple[bool, str | None]:
        if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_KEY"):
            return False, "SUPABASE_URL y SUPABASE_KEY son requeridos"
        return True, None
