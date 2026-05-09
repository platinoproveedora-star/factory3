"""Service for fb_groupsearch_saver — registra búsqueda y guarda grupos con dedup."""
from __future__ import annotations

from factory.engine import SupabaseClient


class FbGroupsearchSaverService:

    def ejecutar(self, context: dict) -> dict:
        grupos     = context.get("grupos") or []
        tema       = (context.get("tema_busqueda") or "").strip()
        fuente     = (context.get("fuente") or "ia_sugerido")
        empresa_id = (context.get("empresa_id") or "")
        usuario_id = (context.get("usuario_id") or "")

        if not tema:
            return {"ok": False, "error": "tema_busqueda es requerido"}
        if not isinstance(grupos, list):
            return {"ok": False, "error": "grupos debe ser lista"}

        if context.get("dry_run", False):
            return {"ok": True, "message": "dry_run", "data": context}

        db        = SupabaseClient(context)
        search_id = self._gen_search_id(db)

        db.rest_insert("fb_gs_searches", {
            "search_id":     search_id,
            "empresa_id":    empresa_id,
            "usuario_id":    usuario_id,
            "tema_busqueda": tema,
            "fuente":        fuente,
            "estado":        "guardando",
            "total_grupos":  0,
        })

        saved = self._guardar_grupos(db, grupos, fuente, search_id, empresa_id)
        estado = "completada" if saved > 0 else "vacía"

        db.rest_update(
            "fb_gs_searches",
            {"estado": estado, "total_grupos": saved},
            {"search_id": search_id},
        )

        return {
            "ok": True,
            "message": f"{saved} grupos guardados (search_id: {search_id})",
            "data": {
                "search_id":     search_id,
                "tema_busqueda": tema,
                "total_grupos":  saved,
                "estado":        estado,
                "fuente":        fuente,
            },
        }

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _gen_search_id(self, db: SupabaseClient) -> str:
        r = db.rest_select("fb_gs_searches", select="id", limit=9999)
        n = len(r.get("data") or []) + 1
        return f"SRCH-{n:04d}"

    def _guardar_grupos(
        self,
        db: SupabaseClient,
        grupos: list,
        fuente: str,
        search_id: str,
        empresa_id: str,
    ) -> int:
        existing_r = db.rest_select(
            "fb_gs_groups",
            filters={"empresa_id": empresa_id} if empresa_id else {},
            select="grupo_url",
            limit=9999,
        )
        existing_urls = {
            r.get("grupo_url", "")
            for r in (existing_r.get("data") or [])
            if r.get("grupo_url")
        }

        saved = 0
        for g in grupos:
            url = (g.get("grupo_url") or "").strip()
            if url and url in existing_urls:
                continue
            row = {
                "search_id":           search_id,
                "empresa_id":          empresa_id,
                "grupo_nombre":        g.get("grupo_nombre", ""),
                "grupo_url":           url,
                "descripcion":         g.get("descripcion", ""),
                "miembros_estimados":  g.get("miembros_estimados"),
                "ubicacion_detectada": g.get("ubicacion_detectada", ""),
                "fuente":              fuente,
            }
            r = db.rest_insert("fb_gs_groups", row)
            if r.get("ok"):
                saved += 1
                if url:
                    existing_urls.add(url)
        return saved
