"""Service for fb_groupsearch_delete — borra búsqueda y sus grupos."""
from __future__ import annotations

from factory.engine import SupabaseClient


class FbGroupsearchDeleteService:

    def ejecutar(self, context: dict) -> dict:
        search_id = (context.get("search_id") or "").strip()
        if not search_id:
            return {"ok": False, "error": "search_id es requerido"}

        if context.get("dry_run", False):
            return {"ok": True, "message": "dry_run", "data": context}

        db = SupabaseClient(context)

        r_groups = db.rest_delete("fb_gs_groups", {"search_id": search_id})
        r_search = db.rest_delete("fb_gs_searches", {"search_id": search_id})

        if not r_search.get("ok"):
            return {"ok": False, "error": r_search.get("error", "error al eliminar búsqueda")}

        return {
            "ok": True,
            "message": f"Búsqueda {search_id} eliminada",
            "data": {"search_id": search_id},
        }
