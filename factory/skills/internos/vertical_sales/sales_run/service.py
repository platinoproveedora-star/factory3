"""Bot mode multicanal — orquesta flujo completo: router → lead → score → followup."""
from __future__ import annotations
from pathlib import Path


def _runner():
    from factory.engine import SkillLoader, SkillRunner
    root     = Path(__file__).parent.parent.parent  # factory/skills/internos
    ext_root = root.parent / "externos"
    ext_root.mkdir(parents=True, exist_ok=True)
    loader = SkillLoader(
        internal_root=root,
        external_root=ext_root,
        extra_roots={"meta": root.parent / "meta", "eval": root.parent / "eval"},
    )
    return SkillRunner(loader)


def _run(name: str, ctx: dict) -> dict:
    return _runner().run(name, ctx, source="internos")


class SalesRunService:

    def ejecutar(self, context: dict) -> dict:
        # Soporte bot (update/state) y llamada directa
        if "update" in context:
            return self._from_bot(context)
        return self._from_context(context)

    def _from_bot(self, context: dict) -> dict:
        import os
        update  = context.get("update", {})
        state   = context.get("state", {})
        message = update.get("message", {})
        texto   = (message.get("text") or "").strip()
        from_u  = message.get("from", {})
        user_id = str(from_u.get("id", "")).strip()
        chat_id = str(message.get("chat", {}).get("id", user_id)).strip()
        empresa_id = os.getenv("SALES_EMPRESA_ID", "sales_default")
        dry_run    = state.get("dry_run", False)

        if not texto:
            return {"ok": True, "data": {
                "response":     "Escribe tu mensaje y te ayudo. /ayuda_sales para comandos.",
                "state":        state,
            }}

        if texto.lower() in ("/ayuda_sales", "/ayuda"):
            return {"ok": True, "data": {
                "response": (
                    "<b>Modo Ventas</b>\n\n"
                    "Escribe tu consulta y la procesaré como lead.\n\n"
                    "/ayuda_sales — esta ayuda\n"
                    "/salir — salir del modo ventas"
                ),
                "state": state,
            }}

        ctx = {
            "canal": "telegram", "user_id": user_id, "chat_id": chat_id,
            "texto": texto, "empresa_id": empresa_id,
            "raw_payload": update, "dry_run": dry_run,
        }
        result = self._from_context(ctx)
        if not result.get("ok"):
            return {"ok": True, "data": {
                "response": f"Error: {result.get('error', 'desconocido')}",
                "state": state,
            }}
        d = result["data"]
        nivel = d.get("nivel", "frio")
        emoji = {"caliente": "🔥", "tibio": "🌡", "frio": "❄"}.get(nivel, "")
        resp = (
            f"{emoji} Lead registrado\n"
            f"Folio: {d.get('lead_folio', '-')}\n"
            f"Intent: {d.get('intent', '-')} | Score: {d.get('score', 0)} ({nivel})\n"
        )
        if d.get("mensaje_sugerido"):
            resp += f"\nSiguiente paso: {d['mensaje_sugerido']}"
        return {"ok": True, "data": {"response": resp, "state": state}}

    def _from_context(self, context: dict) -> dict:
        canal       = context.get("canal", "telegram").strip()
        user_id     = str(context.get("user_id", "")).strip()
        chat_id     = str(context.get("chat_id", "")).strip()
        texto       = context.get("texto", "").strip()
        empresa_id  = context.get("empresa_id", "").strip()
        raw_payload = context.get("raw_payload") or {}
        intent_hint = str(context.get("intent", "")).strip()
        nombre      = str(context.get("nombre", "")).strip()
        telefono    = str(context.get("telefono", "")).strip()
        email       = str(context.get("email", "")).strip()
        dry_run     = context.get("dry_run", True)

        if not user_id or not empresa_id or not texto:
            return {"ok": False, "error": "user_id, empresa_id y texto son requeridos"}

        base = {"empresa_id": empresa_id, "dry_run": dry_run}

        # 1. Normalizar y clasificar intención
        r1 = _run("vertical_sales/communication_router_system", {
            **base, "canal": canal, "user_id": user_id,
            "chat_id": chat_id, "texto": texto, "raw_payload": raw_payload,
            "intent": intent_hint,
        })
        if not r1.get("ok"):
            return r1
        d1     = r1["data"]
        intent = d1.get("intent", "otro")

        # 2. Pipeline de lead (dedup + create)
        r2 = _run("vertical_sales/lead_pipeline_system", {
            **base, "canal": canal, "user_id": user_id, "intent": intent, "texto": texto,
            "nombre": nombre, "telefono": telefono, "email": email,
        })
        if not r2.get("ok"):
            return r2
        d2      = r2["data"]
        lead_id = d2.get("lead_id")
        es_nuevo = d2.get("es_nuevo", True)

        if not lead_id:
            return {"ok": True, "data": {
                "intent":       intent,
                "lead_creado":  False,
                "mensaje":      d2.get("mensaje"),
            }}

        # 3. Registrar mensaje entrante
        _run("vertical_sales/conversation_log_system", {
            **base, "lead_id": lead_id, "canal": canal, "direccion": "in", "texto": texto,
        })

        # 4. Score del lead
        r4    = _run("vertical_sales/lead_score_system", {
            **base, "lead_id": lead_id, "intent": intent, "texto": texto, "canal": canal,
        })
        score = r4.get("data", {}).get("score", 0) if r4.get("ok") else 0
        nivel = r4.get("data", {}).get("nivel", "frio") if r4.get("ok") else "frio"

        # 5. Orquestar siguiente acción
        r5     = _run("vertical_sales/automation_orchestrator_system", {
            **base, "lead_id": lead_id, "intent": intent, "score": score, "es_nuevo": es_nuevo,
        })
        accion = r5.get("data", {}).get("accion", "monitorear") if r5.get("ok") else "monitorear"

        # 6. Generar mensaje de seguimiento
        r6      = _run("vertical_sales/ai_followup_system", {
            **base, "lead_id": lead_id, "intent": intent, "nombre": nombre or "cliente",
        })
        mensaje = r6.get("data", {}).get("mensaje_sugerido", "") if r6.get("ok") else ""

        return {"ok": True, "data": {
            "event_id":         d1.get("event_id"),
            "lead_id":          lead_id,
            "lead_folio":       d2.get("folio"),
            "es_nuevo":         es_nuevo,
            "intent":           intent,
            "score":            score,
            "nivel":            nivel,
            "accion":           accion,
            "mensaje_sugerido": mensaje,
        }}
