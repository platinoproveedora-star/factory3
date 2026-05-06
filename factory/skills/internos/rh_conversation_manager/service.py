"""Service for rh_conversation_manager - get/update/reset conversation state."""

from __future__ import annotations

from factory.engine import SupabaseClient

_ACCIONES  = {"obtener", "actualizar", "reiniciar"}
_ESTADOS   = {"sin_flujo", "iniciando", "haciendo_cuestionario", "esperando_respuesta", "finalizado", "modo_admin", "modo_prueba"}


class RhConversationManagerService:

    def ejecutar(self, context: dict) -> dict:
        accion          = context.get("accion", "").strip()
        conversation_id = context.get("conversation_id", "").strip()

        if not accion or accion not in _ACCIONES:
            return {"ok": False, "error": f"accion requerida — validas: {', '.join(_ACCIONES)}"}
        if not conversation_id:
            return {"ok": False, "error": "conversation_id es requerido"}

        db = SupabaseClient(context)

        if accion == "obtener":
            return self._obtener(db, conversation_id)
        if accion == "actualizar":
            return self._actualizar(db, conversation_id, context)
        if accion == "reiniciar":
            return self._reiniciar(db, conversation_id)

    def _obtener(self, db: SupabaseClient, conversation_id: str) -> dict:
        result = db.rest_select("conversaciones", filters={"id": conversation_id}, limit=1)
        if not result.get("ok"):
            return result
        rows = result.get("data") or []
        if not rows:
            return {"ok": False, "error": f"conversacion no encontrada: {conversation_id}"}
        return {"ok": True, "data": rows[0]}

    def _actualizar(self, db: SupabaseClient, conversation_id: str, context: dict) -> dict:
        campos = {}
        if "estado" in context:
            if context["estado"] not in _ESTADOS:
                return {"ok": False, "error": f"estado invalido — validos: {', '.join(_ESTADOS)}"}
            campos["estado"] = context["estado"]
        if "cuestionario_paso" in context:
            paso = context["cuestionario_paso"]
            if not isinstance(paso, int) or paso < 0:
                return {"ok": False, "error": "cuestionario_paso debe ser entero >= 0"}
            campos["cuestionario_paso"] = paso
        if "datos_temp" in context:
            campos["datos_temp"] = context["datos_temp"]

        if not campos:
            return {"ok": False, "error": "ningun campo para actualizar"}

        result = db.rest_update("conversaciones", values=campos, filters={"id": conversation_id})
        if not result.get("ok"):
            return result
        rows = result.get("data") or []
        return {"ok": True, "message": "conversacion actualizada", "data": rows[0] if rows else {"id": conversation_id}}

    def _reiniciar(self, db: SupabaseClient, conversation_id: str) -> dict:
        result = db.rest_update(
            "conversaciones",
            values={"estado": "iniciando", "cuestionario_paso": 0, "datos_temp": None},
            filters={"id": conversation_id},
        )
        if not result.get("ok"):
            return result
        return {"ok": True, "message": "conversacion reiniciada", "data": {"conversation_id": conversation_id}}
