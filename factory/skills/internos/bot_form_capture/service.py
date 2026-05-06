"""Service for bot_form_capture - step-by-step questionnaire with Supabase persistence."""

from __future__ import annotations

from factory.engine import SupabaseClient


class BotFormCaptureService:

    def ejecutar(self, context: dict) -> dict:
        conversation_id = context.get("conversation_id", "").strip()
        candidato_id = context.get("candidato_id", "").strip()
        vacante_id = context.get("vacante_id", "").strip()
        preguntas = context.get("preguntas", [])
        message_text = (context.get("message_text") or "").strip()

        if not conversation_id:
            return {"ok": False, "error": "conversation_id es requerido"}
        if not candidato_id:
            return {"ok": False, "error": "candidato_id es requerido"}
        if not vacante_id:
            return {"ok": False, "error": "vacante_id es requerido"}
        if not preguntas or not isinstance(preguntas, list):
            return {"ok": False, "error": "preguntas debe ser una lista no vacia"}

        db = SupabaseClient(context)

        conv = self._get_conversacion(db, conversation_id)
        if not conv.get("ok"):
            return conv
        conv_data = conv["data"]
        if not conv_data:
            return {"ok": False, "error": f"conversacion no encontrada: {conversation_id}"}

        paso = conv_data.get("cuestionario_paso", 0)
        total = len(preguntas)

        # Si hay respuesta del usuario, guardarla para la pregunta actual (paso actual = pregunta ya enviada)
        if message_text and paso > 0:
            save = self._guardar_respuesta(db, candidato_id, vacante_id, preguntas[paso - 1], message_text, paso - 1)
            if not save.get("ok"):
                return save

        # Si ya se respondieron todas las preguntas
        if paso >= total:
            self._actualizar_conversacion(db, conversation_id, total, "finalizado")
            return {
                "ok": True,
                "data": {
                    "completado": True,
                    "pregunta_siguiente": None,
                    "paso_actual": total,
                    "total_pasos": total,
                    "message": "Cuestionario completado",
                },
            }

        # Devolver la pregunta actual y avanzar el paso
        pregunta_siguiente = preguntas[paso]
        nuevo_paso = paso + 1
        nuevo_estado = "haciendo_cuestionario" if nuevo_paso < total else "esperando_respuesta"
        self._actualizar_conversacion(db, conversation_id, nuevo_paso, nuevo_estado)

        return {
            "ok": True,
            "data": {
                "completado": False,
                "pregunta_siguiente": pregunta_siguiente,
                "paso_actual": nuevo_paso,
                "total_pasos": total,
                "message": f"Pregunta {nuevo_paso} de {total}",
            },
        }

    # --- helpers ---

    def _get_conversacion(self, db: SupabaseClient, conversation_id: str) -> dict:
        result = db.rest_select(
            "conversaciones",
            filters={"id": conversation_id},
            select="id,cuestionario_paso,estado",
            limit=1,
        )
        if not result.get("ok"):
            return result
        rows = result.get("data") or []
        return {"ok": True, "data": rows[0] if rows else None}

    def _guardar_respuesta(
        self,
        db: SupabaseClient,
        candidato_id: str,
        vacante_id: str,
        pregunta: str,
        respuesta: str,
        orden: int,
    ) -> dict:
        return db.rest_insert("respuestas", {
            "candidato_id": candidato_id,
            "vacante_id": vacante_id,
            "pregunta": pregunta,
            "respuesta": respuesta,
            "orden": orden,
        })

    def _actualizar_conversacion(
        self,
        db: SupabaseClient,
        conversation_id: str,
        paso: int,
        estado: str,
    ) -> dict:
        return db.rest_update(
            "conversaciones",
            values={"cuestionario_paso": paso, "estado": estado},
            filters={"id": conversation_id},
        )
