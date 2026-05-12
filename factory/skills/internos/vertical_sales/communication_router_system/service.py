"""Normaliza mensajes multicanal, clasifica intención comercial con IA y guarda evento."""
from __future__ import annotations
import json, os, urllib.request
from datetime import datetime, timezone

_SCHEMA  = "sales"
_CANALES = {"telegram", "whatsapp", "instagram", "instagram_dm", "instagram_comment", "instagram_lead_form", "web"}
_INTENTS = {
    "consulta_comercial": "Pregunta sobre producto o servicio",
    "solicitud_precio":   "Pide precio o cotización",
    "disponibilidad":     "Pregunta disponibilidad o stock",
    "agendar_cita":       "Quiere agendar visita o llamada",
    "seguimiento":        "Da seguimiento a contacto previo",
    "queja":              "Expresa queja o insatisfacción",
    "spam":               "Mensaje irrelevante o spam",
    "otro":               "No encaja en categoría comercial",
}


class CommunicationRouterService:

    def ejecutar(self, context: dict) -> dict:
        canal       = context.get("canal", "telegram").strip()
        user_id     = str(context.get("user_id", "")).strip()
        chat_id     = str(context.get("chat_id", "")).strip()
        texto       = str(context.get("texto", "")).strip()
        empresa_id  = context.get("empresa_id", "").strip()
        raw_payload = context.get("raw_payload") or {}
        dry_run     = context.get("dry_run", True)

        if canal not in _CANALES:
            return {"ok": False, "error": f"canal inválido — válidos: {', '.join(_CANALES)}"}
        if not user_id:
            return {"ok": False, "error": "user_id requerido"}
        if not empresa_id:
            return {"ok": False, "error": "empresa_id requerido"}
        if not texto:
            return {"ok": False, "error": "texto requerido"}

        intent_input = str(context.get("intent", "")).strip()
        intent = intent_input if intent_input in _INTENTS else self._classify_intent(texto)
        evento = {
            "canal":      canal,
            "user_id":    user_id,
            "chat_id":    chat_id,
            "texto":      texto,
            "intent":     intent,
            "empresa_id": empresa_id,
            "timestamp":  datetime.now(timezone.utc).isoformat(),
        }

        if dry_run:
            return {"ok": True, "data": {
                "evento_normalizado": evento,
                "intent":             intent,
                "empresa_id":         empresa_id,
                "usuario_id":         user_id,
                "event_id":           "EVT-DRY",
                "dry_run":            True,
            }}

        url = os.getenv("SUPABASE_URL", "").rstrip("/")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        if not url or not key:
            return {"ok": False, "error": "Faltan SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY"}

        folio = self._next_folio("EVT", "communication_events", url, key)
        saved = self._insert("communication_events", {
            "folio":       folio,
            "empresa_id":  empresa_id,
            "canal":       canal,
            "user_id":     user_id,
            "chat_id":     chat_id or None,
            "texto":       texto,
            "intent":      intent,
            "raw_payload": raw_payload,
        }, url, key)
        if not saved.get("ok"):
            return saved

        return {"ok": True, "data": {
            "evento_normalizado": evento,
            "intent":             intent,
            "empresa_id":         empresa_id,
            "usuario_id":         user_id,
            "event_id":           folio,
        }}

    def _classify_intent(self, texto: str) -> str:
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            return "otro"
        actions = "\n".join(f"- {k}: {v}" for k, v in _INTENTS.items())
        prompt = (
            f"Clasifica la intención de este mensaje en una sola clave.\n"
            f"Opciones:\n{actions}\n\n"
            f"Mensaje: {texto}\n\n"
            f'Responde SOLO con JSON: {{"intent": "<clave>"}}'
        )
        try:
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=json.dumps({
                    "model":      "claude-haiku-4-5-20251001",
                    "max_tokens": 64,
                    "messages":   [{"role": "user", "content": prompt}],
                }).encode(),
                headers={
                    "content-type":      "application/json",
                    "x-api-key":         api_key,
                    "anthropic-version": "2023-06-01",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as r:
                text = json.loads(r.read().decode())["content"][0]["text"].strip()
                intent = json.loads(text).get("intent", "otro")
                return intent if intent in _INTENTS else "otro"
        except Exception:
            return "otro"

    def _next_folio(self, prefix: str, table: str, url: str, key: str) -> str:
        try:
            req = urllib.request.Request(
                f"{url}/rest/v1/{table}?select=folio&order=created_at.desc&limit=1",
                headers={"apikey": key, "Authorization": f"Bearer {key}", "Accept-Profile": _SCHEMA},
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                rows = json.loads(r.read().decode())
                if rows:
                    return f"{prefix}-{int(rows[0]['folio'].split('-')[-1]) + 1:03d}"
        except Exception:
            pass
        return f"{prefix}-001"

    def _insert(self, table: str, row: dict, url: str, key: str) -> dict:
        try:
            req = urllib.request.Request(
                f"{url}/rest/v1/{table}",
                data=json.dumps(row).encode(),
                headers={
                    "apikey":          key,
                    "Authorization":   f"Bearer {key}",
                    "Content-Type":    "application/json",
                    "Content-Profile": _SCHEMA,
                    "Prefer":          "return=representation",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                rows = json.loads(r.read().decode())
                return {"ok": True, "data": rows[0] if rows else row}
        except Exception as e:
            return {"ok": False, "error": str(e)}
