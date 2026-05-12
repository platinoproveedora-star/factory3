"""Registra y consulta publicaciones de Facebook en Supabase."""

from __future__ import annotations

from datetime import datetime, timezone

from factory.engine import SupabaseClient


class FacebookPostTrackerService:

    def ejecutar(self, context: dict) -> dict:
        accion: str = context.get("accion", "registrar")

        if accion == "registrar":
            return self._registrar(context)
        if accion == "listar":
            return self._listar(context)
        if accion == "puede_publicar":
            return self._puede_publicar(context)
        return {"ok": False, "error": f"accion desconocida: {accion}"}

    def _registrar(self, context: dict) -> dict:
        vacante_id:  str  = context.get("vacante_id") or ""
        grupo_url:   str  = context.get("grupo_url") or ""
        grupo_nombre: str = context.get("grupo_nombre") or ""
        texto:       str  = context.get("texto") or ""
        publicado:   bool = context.get("publicado", False)
        dry_run:     bool = context.get("dry_run", False)
        empresa_id:  str  = context.get("empresa_id") or ""

        if not grupo_url:
            return {"ok": False, "error": "grupo_url es requerido"}

        db  = SupabaseClient({})
        row = {
            "vacante_id":   vacante_id,
            "empresa_id":   empresa_id,
            "grupo_url":    grupo_url,
            "grupo_nombre": grupo_nombre,
            "texto":        texto[:500],
            "publicado":    publicado,
            "dry_run":      dry_run,
            "fecha":        datetime.now(timezone.utc).isoformat(),
        }
        r = db.rest_insert("fb_publicaciones", row)
        if not r.get("ok"):
            return {"ok": False, "error": f"Error al guardar: {r.get('error')}"}
        return {"ok": True, "data": {"registrado": True, "fila": row}}

    def _listar(self, context: dict) -> dict:
        vacante_id: str = context.get("vacante_id") or ""
        empresa_id: str = context.get("empresa_id") or ""
        limit:      int = int(context.get("limit", 20))

        db      = SupabaseClient({})
        filters = {}
        if vacante_id:
            filters["vacante_id"] = vacante_id
        if empresa_id:
            filters["empresa_id"] = empresa_id

        r    = db.rest_select("fb_publicaciones", filters=filters, select="*", limit=limit)
        rows = (r.get("data") or []) if r.get("ok") else []
        return {"ok": True, "data": {"publicaciones": rows, "total": len(rows)}}

    def _puede_publicar(self, context: dict) -> dict:
        """Verifica si ya se publicó en este grupo para esta vacante recientemente."""
        grupo_url:  str = context.get("grupo_url") or ""
        vacante_id: str = context.get("vacante_id") or ""
        cooldown_h: int = int(context.get("cooldown_horas", 72))

        if not grupo_url:
            return {"ok": False, "error": "grupo_url es requerido"}

        db = SupabaseClient({})
        filters: dict = {"grupo_url": grupo_url, "publicado": True}
        if vacante_id:
            filters["vacante_id"] = vacante_id

        r    = db.rest_select("fb_publicaciones", filters=filters, select="fecha", limit=1)
        rows = (r.get("data") or []) if r.get("ok") else []

        if not rows:
            return {"ok": True, "data": {"puede": True, "razon": "sin publicaciones previas"}}

        ultima_fecha = rows[0].get("fecha", "")
        if ultima_fecha:
            ultima = datetime.fromisoformat(ultima_fecha.replace("Z", "+00:00"))
            ahora  = datetime.now(timezone.utc)
            horas  = (ahora - ultima).total_seconds() / 3600
            if horas < cooldown_h:
                return {"ok": True, "data": {
                    "puede":  False,
                    "razon":  f"publicado hace {round(horas, 1)}h — cooldown: {cooldown_h}h",
                    "horas_restantes": round(cooldown_h - horas, 1),
                }}

        return {"ok": True, "data": {"puede": True, "razon": "cooldown superado"}}
