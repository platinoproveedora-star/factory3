"""Notifica al agente de ventas por Telegram cuando llega lead caliente."""
from __future__ import annotations
import json, os, urllib.request

_SCHEMA       = "sales"
_UMBRAL_SCORE = 70


class SalesNotifyAgentService:

    def ejecutar(self, context: dict) -> dict:
        lead_id    = context.get("lead_id", "").strip()
        empresa_id = context.get("empresa_id", "").strip()
        chat_id    = str(context.get("agent_chat_id", "")).strip()
        score      = int(context.get("score", 0))
        nivel      = context.get("nivel", "frio").strip()
        mensaje    = context.get("mensaje", "").strip()
        bot_token  = context.get("bot_token", "").strip() or os.getenv("FACTORY3_ADMIN_BOT_TOKEN", "")
        dry_run    = context.get("dry_run", True)

        if not lead_id:
            return {"ok": False, "error": "lead_id requerido"}
        if not empresa_id:
            return {"ok": False, "error": "empresa_id requerido"}
        if not chat_id:
            return {"ok": False, "error": "agent_chat_id requerido"}

        if score < _UMBRAL_SCORE and nivel != "caliente":
            return {"ok": True, "data": {
                "enviado":  False,
                "razon":    f"score {score} < {_UMBRAL_SCORE} y nivel={nivel} — notificación omitida",
            }}

        url = os.getenv("SUPABASE_URL", "").rstrip("/")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        lead_info = self._get_lead(lead_id, url, key) if url and key else {}

        folio  = lead_info.get("folio", lead_id)
        nombre = lead_info.get("nombre") or "Sin nombre"
        canal  = lead_info.get("canal", "desconocido")

        texto = mensaje or (
            f"🔥 <b>Lead caliente</b>\n"
            f"Folio: {folio}\n"
            f"Nombre: {nombre}\n"
            f"Canal: {canal}\n"
            f"Score: {score}/100\n"
            f"Empresa: {empresa_id}"
        )

        if dry_run:
            return {"ok": True, "data": {"enviado": False, "mensaje": texto, "dry_run": True}}

        if not bot_token:
            return {"ok": False, "error": "bot_token o FACTORY3_ADMIN_BOT_TOKEN requerido"}

        return self._send(bot_token, chat_id, texto)

    def _get_lead(self, lead_id: str, url: str, key: str) -> dict:
        try:
            req = urllib.request.Request(
                f"{url}/rest/v1/leads?id=eq.{lead_id}&select=folio,nombre,canal&limit=1",
                headers={"apikey": key, "Authorization": f"Bearer {key}", "Accept-Profile": _SCHEMA},
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                rows = json.loads(r.read().decode())
                return rows[0] if rows else {}
        except Exception:
            return {}

    def _send(self, token: str, chat_id: str, texto: str) -> dict:
        try:
            req = urllib.request.Request(
                f"https://api.telegram.org/bot{token}/sendMessage",
                data=json.dumps({"chat_id": chat_id, "text": texto, "parse_mode": "HTML"}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                resp = json.loads(r.read().decode())
                if resp.get("ok"):
                    return {"ok": True, "data": {"enviado": True, "message_id": resp["result"]["message_id"]}}
                return {"ok": False, "error": resp.get("description", "Error Telegram")}
        except Exception as e:
            return {"ok": False, "error": str(e)}
