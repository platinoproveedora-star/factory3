"""Service for fb_groupsearch_list — retorna búsquedas guardadas."""
from __future__ import annotations

from factory.engine import SupabaseClient


class FbGroupsearchListService:

    def ejecutar(self, context: dict) -> dict:
        empresa_id = (context.get("empresa_id") or "")
        limit      = int(context.get("limit") or 200)

        db      = SupabaseClient(context)
        filters = {"empresa_id": empresa_id} if empresa_id else {}
        r       = db.rest_select(
            "fb_gs_searches",
            filters=filters,
            select="*",
            limit=limit,
            order="created_at.desc",
        )

        if not r.get("ok"):
            return {"ok": False, "error": r.get("error", "error desconocido")}

        return {"ok": True, "data": r.get("data") or []}
