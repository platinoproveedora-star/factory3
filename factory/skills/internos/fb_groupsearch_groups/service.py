"""Service for fb_groupsearch_groups — retorna grupos de una búsqueda."""
from __future__ import annotations

from factory.engine import SupabaseClient


class FbGroupsearchGroupsService:

    def ejecutar(self, context: dict) -> dict:
        search_id  = (context.get("search_id") or "").strip()
        empresa_id = (context.get("empresa_id") or "")
        limit      = int(context.get("limit") or 500)

        db      = SupabaseClient(context)
        filters: dict = {}
        if search_id:
            filters["search_id"] = search_id
        if empresa_id:
            filters["empresa_id"] = empresa_id

        r = db.rest_select(
            "fb_gs_groups",
            filters=filters,
            select="*",
            limit=limit,
            order="created_at.desc",
        )

        if not r.get("ok"):
            return {"ok": False, "error": r.get("error", "error desconocido")}

        return {"ok": True, "data": r.get("data") or []}
