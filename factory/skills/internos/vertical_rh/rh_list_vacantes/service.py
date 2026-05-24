"""Lista filtrable de vacantes RH."""
from __future__ import annotations
import os
from factory.engine import SupabaseClient

_EMPRESA_ID = os.getenv("RH_EMPRESA_ID", "rh_empresa_1")


class RhListVacantesService:

    def ejecutar(self, context: dict) -> dict:
        empresa_id = context.get("empresa_id", _EMPRESA_ID)
        estado     = context.get("estado", "")
        tipo       = context.get("tipo", "")
        buscar     = context.get("buscar", "").lower()
        limit      = min(int(context.get("limit", 200)), 500)

        db = SupabaseClient(context)
        filters = {"empresa_id": empresa_id}
        if estado:
            filters["estado"] = f"eq.{estado}"
        if tipo:
            filters["tipo"] = f"eq.{tipo}"

        r = db.rest_select("vacantes", filters=filters,
                           select="id,folio,titulo,descripcion,estado,tipo,canal,created_at",
                           limit=limit)
        if not r.get("ok"):
            return {"ok": False, "error": r.get("error", "error consultando vacantes")}

        rows = r.get("data") or []
        if buscar:
            rows = [v for v in rows if buscar in (v.get("titulo") or "").lower()]

        return {
            "ok": True,
            "data": {
                "rows":  rows,
                "total": len(rows),
            },
        }
