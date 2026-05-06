"""Service for rh_vacante_store - CRUD de vacantes en Supabase."""

from __future__ import annotations

from factory.engine import SupabaseClient

_ACCIONES = {"crear", "leer", "listar", "actualizar"}
_ESTADOS = {"activa", "pausada", "cerrada"}


class RhVacanteStoreService:

    def ejecutar(self, context: dict) -> dict:
        accion = context.get("accion", "").strip()
        if not accion or accion not in _ACCIONES:
            return {"ok": False, "error": f"accion requerida — validas: {', '.join(_ACCIONES)}"}

        db = SupabaseClient(context)

        if accion == "crear":
            return self._crear(db, context)
        if accion == "leer":
            return self._leer(db, context)
        if accion == "listar":
            return self._listar(db, context)
        if accion == "actualizar":
            return self._actualizar(db, context)

    def _crear(self, db: SupabaseClient, context: dict) -> dict:
        empresa_id = context.get("empresa_id", "").strip()
        titulo = context.get("titulo", "").strip()
        if not empresa_id:
            return {"ok": False, "error": "empresa_id es requerido para crear"}
        if not titulo:
            return {"ok": False, "error": "titulo es requerido para crear"}

        payload = {
            "empresa_id": empresa_id,
            "titulo": titulo,
            "descripcion": context.get("descripcion"),
            "requisitos": context.get("requisitos"),
            "canal": context.get("canal"),
            "estado": context.get("estado", "activa"),
        }
        payload = {k: v for k, v in payload.items() if v is not None}

        result = db.rest_insert("vacantes", payload)
        if not result.get("ok"):
            return result
        rows = result.get("data") or []
        vacante = rows[0] if isinstance(rows, list) and rows else rows
        return {"ok": True, "message": f"vacante '{titulo}' creada", "data": vacante}

    def _leer(self, db: SupabaseClient, context: dict) -> dict:
        vacante_id = context.get("vacante_id", "").strip()
        if not vacante_id:
            return {"ok": False, "error": "vacante_id es requerido para leer"}
        result = db.rest_select("vacantes", filters={"id": vacante_id}, limit=1)
        if not result.get("ok"):
            return result
        rows = result.get("data") or []
        if not rows:
            return {"ok": False, "error": f"vacante no encontrada: {vacante_id}"}
        return {"ok": True, "data": rows[0]}

    def _listar(self, db: SupabaseClient, context: dict) -> dict:
        filters = {}
        if context.get("empresa_id"):
            filters["empresa_id"] = context["empresa_id"]
        if context.get("estado"):
            filters["estado"] = context["estado"]
        result = db.rest_select("vacantes", filters=filters, order="created_at.desc")
        if not result.get("ok"):
            return result
        return {"ok": True, "data": result.get("data") or []}

    def _actualizar(self, db: SupabaseClient, context: dict) -> dict:
        vacante_id = context.get("vacante_id", "").strip()
        if not vacante_id:
            return {"ok": False, "error": "vacante_id es requerido para actualizar"}

        campos = {k: context[k] for k in ("titulo", "descripcion", "requisitos", "canal", "estado") if k in context}
        if not campos:
            return {"ok": False, "error": "ningun campo para actualizar"}
        if "estado" in campos and campos["estado"] not in _ESTADOS:
            return {"ok": False, "error": f"estado invalido — validos: {', '.join(_ESTADOS)}"}

        result = db.rest_update("vacantes", values=campos, filters={"id": vacante_id})
        if not result.get("ok"):
            return result
        rows = result.get("data") or []
        vacante = rows[0] if isinstance(rows, list) and rows else rows
        return {"ok": True, "message": "vacante actualizada", "data": vacante}
