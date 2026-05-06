"""Service for bot_inbox_router - routes incoming messages to the correct flow."""

from __future__ import annotations

from factory.engine import SupabaseClient

_CANALES_VALIDOS = {"telegram", "instagram", "facebook", "whatsapp", "web"}
_MODOS_VALIDOS = {"normal", "admin", "prueba"}


class BotInboxRouterService:

    def ejecutar(self, context: dict) -> dict:
        canal = context.get("canal", "").strip()
        user_id = str(context.get("user_id", "")).strip()
        empresa_id = context.get("empresa_id", "").strip()
        vacante_id = context.get("vacante_id", "").strip()
        modo = context.get("modo", "normal").strip()

        if not canal or canal not in _CANALES_VALIDOS:
            return {"ok": False, "error": f"canal invalido — validos: {', '.join(_CANALES_VALIDOS)}"}
        if not user_id:
            return {"ok": False, "error": "user_id es requerido"}
        if not empresa_id:
            return {"ok": False, "error": "empresa_id es requerido"}
        if not vacante_id:
            return {"ok": False, "error": "vacante_id es requerido"}
        if modo not in _MODOS_VALIDOS:
            return {"ok": False, "error": f"modo invalido — validos: {', '.join(_MODOS_VALIDOS)}"}

        if modo == "admin":
            return {
                "ok": True,
                "data": {
                    "flujo_destino": "admin",
                    "accion_siguiente": "iniciar",
                    "conversation_id": None,
                    "candidate_id": None,
                    "estado_conversacion": "modo_admin",
                    "requiere_humano": False,
                },
            }

        db = SupabaseClient(context)

        candidato = self._buscar_candidato(db, canal, user_id, vacante_id)
        if not candidato.get("ok"):
            return candidato

        candidato_data = candidato.get("data")

        if candidato_data:
            candidate_id = candidato_data["id"]
            conv = self._buscar_conversacion(db, candidate_id, vacante_id)
            if not conv.get("ok"):
                return conv
            conv_data = conv.get("data")
            if conv_data:
                return self._rutear_existente(conv_data, candidate_id)
            conv_nueva = self._crear_conversacion(db, candidate_id, vacante_id, canal)
            if not conv_nueva.get("ok"):
                return conv_nueva
            return self._respuesta_nueva(conv_nueva["data"]["id"], candidate_id)

        nuevo_candidato = self._crear_candidato(db, vacante_id, canal, user_id)
        if not nuevo_candidato.get("ok"):
            return nuevo_candidato
        candidate_id = nuevo_candidato["data"]["id"]

        conv_nueva = self._crear_conversacion(db, candidate_id, vacante_id, canal)
        if not conv_nueva.get("ok"):
            return conv_nueva

        return self._respuesta_nueva(conv_nueva["data"]["id"], candidate_id)

    # --- helpers ---

    def _buscar_candidato(self, db: SupabaseClient, canal: str, user_id: str, vacante_id: str) -> dict:
        result = db.rest_select(
            "candidatos",
            filters={"canal": canal, "canal_user_id": user_id, "vacante_id": vacante_id},
            limit=1,
        )
        if not result.get("ok"):
            return result
        rows = result.get("data") or []
        return {"ok": True, "data": rows[0] if rows else None}

    def _buscar_conversacion(self, db: SupabaseClient, candidate_id: str, vacante_id: str) -> dict:
        result = db.rest_select(
            "conversaciones",
            filters={"candidato_id": candidate_id, "vacante_id": vacante_id},
            limit=1,
        )
        if not result.get("ok"):
            return result
        rows = result.get("data") or []
        return {"ok": True, "data": rows[0] if rows else None}

    def _crear_candidato(self, db: SupabaseClient, vacante_id: str, canal: str, user_id: str) -> dict:
        result = db.rest_insert("candidatos", {
            "vacante_id": vacante_id,
            "canal": canal,
            "canal_user_id": user_id,
            "estado": "nuevo",
        })
        if not result.get("ok"):
            return result
        rows = result.get("data") or []
        if not rows:
            return {"ok": False, "error": "no se pudo crear el candidato"}
        return {"ok": True, "data": rows[0] if isinstance(rows, list) else rows}

    def _crear_conversacion(self, db: SupabaseClient, candidate_id: str, vacante_id: str, canal: str) -> dict:
        result = db.rest_insert("conversaciones", {
            "candidato_id": candidate_id,
            "vacante_id": vacante_id,
            "canal": canal,
            "estado": "iniciando",
            "cuestionario_paso": 0,
        })
        if not result.get("ok"):
            return result
        rows = result.get("data") or []
        if not rows:
            return {"ok": False, "error": "no se pudo crear la conversacion"}
        return {"ok": True, "data": rows[0] if isinstance(rows, list) else rows}

    def _rutear_existente(self, conv: dict, candidate_id: str) -> dict:
        estado = conv.get("estado", "sin_flujo")
        acciones = {
            "iniciando": "iniciar",
            "haciendo_cuestionario": "continuar",
            "esperando_respuesta": "continuar",
            "finalizado": "finalizar",
        }
        return {
            "ok": True,
            "data": {
                "flujo_destino": "rh_questionnaire",
                "accion_siguiente": acciones.get(estado, "continuar"),
                "conversation_id": conv["id"],
                "candidate_id": candidate_id,
                "estado_conversacion": estado,
                "requiere_humano": estado == "finalizado",
            },
        }

    def _respuesta_nueva(self, conversation_id: str, candidate_id: str) -> dict:
        return {
            "ok": True,
            "data": {
                "flujo_destino": "rh_questionnaire",
                "accion_siguiente": "iniciar",
                "conversation_id": conversation_id,
                "candidate_id": candidate_id,
                "estado_conversacion": "iniciando",
                "requiere_humano": False,
            },
        }
