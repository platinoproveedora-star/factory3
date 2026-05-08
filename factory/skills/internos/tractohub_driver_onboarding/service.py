"""Recopilacion de documentos de operador via Telegram — paso a paso."""

from __future__ import annotations

import os
from datetime import datetime, timezone

from factory.engine import SupabaseClient


# Documentos requeridos en orden
_DOCUMENTOS = [
    {
        "clave":       "ine_frente",
        "nombre":      "INE (frente)",
        "instruccion": "Envía una foto del <b>frente de tu INE</b> (credencial de elector).",
        "tipo":        "foto",
    },
    {
        "clave":       "ine_reverso",
        "nombre":      "INE (reverso)",
        "instruccion": "Ahora envía una foto del <b>reverso de tu INE</b>.",
        "tipo":        "foto",
    },
    {
        "clave":       "licencia_federal",
        "nombre":      "Licencia federal tipo E",
        "instruccion": "Envía una foto de tu <b>licencia federal tipo E</b> (ambos lados en una imagen si es posible).",
        "tipo":        "foto",
    },
    {
        "clave":       "imss",
        "nombre":      "Número IMSS",
        "instruccion": "Escribe tu <b>número de seguridad social (IMSS)</b>. Ejemplo: 12345678901.",
        "tipo":        "texto",
    },
    {
        "clave":       "comprobante_domicilio",
        "nombre":      "Comprobante de domicilio",
        "instruccion": "Envía una foto de tu <b>comprobante de domicilio</b> (agua, luz o teléfono — no mayor a 3 meses).",
        "tipo":        "foto",
    },
    {
        "clave":       "antecedentes",
        "nombre":      "Carta de no antecedentes penales",
        "instruccion": "Envía una foto o PDF de tu <b>carta de no antecedentes penales</b>.",
        "tipo":        "foto",
    },
    {
        "clave":       "foto_perfil",
        "nombre":      "Foto de perfil",
        "instruccion": "Por último, envía una <b>foto tuya de frente</b> con buena iluminación.",
        "tipo":        "foto",
    },
]

_MSG_BIENVENIDA = (
    "¡Bienvenido al proceso de incorporación TractHub! 🚛\n\n"
    "Vamos a recopilar tus documentos paso a paso.\n"
    "Son <b>{total}</b> documentos en total. Puedes pausar y continuar cuando quieras.\n\n"
    "Empecemos:"
)

_MSG_COMPLETADO = (
    "✅ <b>¡Documentos completos!</b>\n\n"
    "Recibimos todos tus documentos. El equipo de TractHub los revisará y te contactará en breve.\n"
    "¡Gracias por tu tiempo!"
)

_MANAGER_CHAT_ID = os.getenv("MANAGER_TELEGRAM_CHAT_ID", "")
_TELEGRAM_TOKEN  = os.getenv("FACTORY3_ADMIN_BOT_TOKEN", "")


class TractohubDriverOnboardingService:

    def ejecutar(self, context: dict) -> dict:
        accion:       str  = context.get("accion", "procesar_mensaje")
        candidato_id: str  = context.get("candidato_id") or ""
        empresa_id:   str  = context.get("empresa_id") or ""

        if not candidato_id:
            return {"ok": False, "error": "candidato_id es requerido"}

        if accion == "iniciar":
            return self._iniciar(candidato_id, empresa_id)

        if accion == "procesar_mensaje":
            return self._procesar_mensaje(context, candidato_id, empresa_id)

        if accion == "estado":
            return self._estado(candidato_id)

        return {"ok": False, "error": f"accion desconocida: {accion}"}

    # ── Iniciar onboarding ─────────────────────────────────────────────────────

    def _iniciar(self, candidato_id: str, empresa_id: str) -> dict:
        db = SupabaseClient({})

        # Limpiar docs previos si los hay
        db.rest_delete("onboarding_docs", filters={"candidato_id": candidato_id})

        # Crear registros pendientes para cada documento
        for doc in _DOCUMENTOS:
            db.rest_insert("onboarding_docs", {
                "candidato_id": candidato_id,
                "empresa_id":   empresa_id,
                "doc_clave":    doc["clave"],
                "doc_nombre":   doc["nombre"],
                "estado":       "pendiente",
                "file_id":      None,
                "valor_texto":  None,
                "fecha":        None,
            })

        primer_doc = _DOCUMENTOS[0]
        return {
            "ok": True,
            "data": {
                "response": (
                    _MSG_BIENVENIDA.format(total=len(_DOCUMENTOS))
                    + "\n\n" + primer_doc["instruccion"]
                ),
                "paso_actual":  1,
                "total_pasos":  len(_DOCUMENTOS),
                "doc_pendiente": primer_doc["clave"],
            },
        }

    # ── Procesar mensaje del driver ────────────────────────────────────────────

    def _procesar_mensaje(self, context: dict, candidato_id: str, empresa_id: str) -> dict:
        update  = context.get("update") or {}
        message = update.get("message") or {}

        # Extraer file_id o texto según tipo de mensaje
        file_id     = None
        valor_texto = None

        if message.get("photo"):
            # Telegram devuelve array de tamaños — tomar el mayor
            fotos   = message["photo"]
            file_id = fotos[-1].get("file_id")
        elif message.get("document"):
            file_id = message["document"].get("file_id")
        elif message.get("text"):
            valor_texto = message["text"].strip()

        db = SupabaseClient({})

        # Obtener siguiente doc pendiente
        r    = db.rest_select(
            "onboarding_docs",
            filters={"candidato_id": candidato_id, "estado": "pendiente"},
            select="id,doc_clave,doc_nombre",
        )
        pendientes = (r.get("data") or []) if r.get("ok") else []

        if not pendientes:
            return {"ok": True, "data": {"response": "Ya completaste todos tus documentos. ¡Gracias!", "completado": True}}

        doc_actual = pendientes[0]
        doc_info   = next((d for d in _DOCUMENTOS if d["clave"] == doc_actual["doc_clave"]), None)

        # Validar que envió lo correcto
        if doc_info and doc_info["tipo"] == "foto" and not file_id:
            return {"ok": True, "data": {
                "response": f"Por favor envía una <b>foto o imagen</b> para: {doc_info['nombre']}.\n\n{doc_info['instruccion']}",
                "completado": False,
            }}
        if doc_info and doc_info["tipo"] == "texto" and not valor_texto:
            return {"ok": True, "data": {
                "response": f"Por favor escribe el dato solicitado: {doc_info['nombre']}.\n\n{doc_info['instruccion']}",
                "completado": False,
            }}

        # Guardar documento recibido
        db.rest_update("onboarding_docs", values={
            "estado":       "recibido",
            "file_id":      file_id,
            "valor_texto":  valor_texto,
            "fecha":        datetime.now(timezone.utc).isoformat(),
        }, filters={"id": doc_actual["id"]})

        # Verificar si quedan pendientes
        r2         = db.rest_select("onboarding_docs", filters={"candidato_id": candidato_id, "estado": "pendiente"}, select="id,doc_clave")
        restantes  = (r2.get("data") or []) if r2.get("ok") else []

        if not restantes:
            self._notificar_manager(candidato_id, empresa_id)
            return {"ok": True, "data": {"response": _MSG_COMPLETADO, "completado": True}}

        # Pedir siguiente documento
        siguiente  = restantes[0]
        sig_info   = next((d for d in _DOCUMENTOS if d["clave"] == siguiente["doc_clave"]), None)
        recibidos  = len(_DOCUMENTOS) - len(restantes)
        response   = (
            f"✅ <b>{doc_actual['doc_nombre']}</b> recibido.\n\n"
            f"[{recibidos + 1}/{len(_DOCUMENTOS)}] {sig_info['instruccion'] if sig_info else 'Siguiente documento:'}"
        )

        return {
            "ok": True,
            "data": {
                "response":      response,
                "completado":    False,
                "paso_actual":   recibidos + 1,
                "total_pasos":   len(_DOCUMENTOS),
                "doc_pendiente": siguiente["doc_clave"],
            },
        }

    # ── Estado del onboarding ──────────────────────────────────────────────────

    def _estado(self, candidato_id: str) -> dict:
        db   = SupabaseClient({})
        r    = db.rest_select("onboarding_docs", filters={"candidato_id": candidato_id}, select="doc_clave,doc_nombre,estado,fecha")
        docs = (r.get("data") or []) if r.get("ok") else []

        recibidos  = [d for d in docs if d["estado"] == "recibido"]
        pendientes = [d for d in docs if d["estado"] == "pendiente"]
        completado = len(pendientes) == 0 and len(docs) > 0

        return {
            "ok": True,
            "data": {
                "candidato_id": candidato_id,
                "completado":   completado,
                "total":        len(docs),
                "recibidos":    len(recibidos),
                "pendientes":   len(pendientes),
                "docs":         docs,
            },
        }

    # ── Notificacion manager ───────────────────────────────────────────────────

    def _notificar_manager(self, candidato_id: str, empresa_id: str) -> None:
        if not _MANAGER_CHAT_ID or not _TELEGRAM_TOKEN:
            return
        try:
            import httpx
            msg = (
                f"📋 <b>Onboarding completo</b>\n"
                f"Candidato: <code>{candidato_id[:12]}</code>\n"
                f"Empresa: {empresa_id}\n"
                f"Todos los documentos recibidos. Listo para revisión."
            )
            httpx.post(
                f"https://api.telegram.org/bot{_TELEGRAM_TOKEN}/sendMessage",
                json={"chat_id": _MANAGER_CHAT_ID, "text": msg, "parse_mode": "HTML"},
                timeout=10,
            )
        except Exception:
            pass
