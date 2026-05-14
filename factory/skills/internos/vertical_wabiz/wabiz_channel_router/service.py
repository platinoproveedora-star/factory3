"""Router IA WhatsApp: historial de conversación + Haiku + wabiz_send_text."""
from __future__ import annotations
import json
import os
import urllib.parse
import urllib.request

_HISTORY_LIMIT = 10
_UA = "FactoryFactory/0.1 (+https://github.com/)"


class WabizChannelRouterService:

    def ejecutar(self, context: dict) -> dict:
        empresa_id   = context.get("empresa_id")
        from_phone   = context.get("from_phone")
        msg_type     = context.get("type", "text")
        body         = context.get("body", "")
        profile_name = context.get("profile_name") or from_phone

        if not empresa_id:
            return {"ok": False, "error": "empresa_id requerido"}
        if not from_phone:
            return {"ok": False, "error": "from_phone requerido"}
        if msg_type != "text" or not body:
            return {"ok": True, "data": {"skipped": True, "reason": "solo se procesa type=text con body"}}

        history  = self._load_history(empresa_id, from_phone)
        ai_reply = self._call_haiku(body, history, profile_name, empresa_id)

        if not ai_reply:
            return {"ok": False, "error": "Haiku no devolvió respuesta"}

        if context.get("dry_run", True):
            return {"ok": True, "data": {"dry_run": True, "reply": ai_reply}}

        send_result = self._send_text(empresa_id, from_phone, ai_reply)
        return {"ok": True, "data": {"reply": ai_reply, "send": send_result}}

    def _load_history(self, empresa_id: str, from_phone: str) -> list[dict]:
        try:
            qs  = urllib.parse.urlencode({
                "empresa_id": f"eq.{empresa_id}",
                "from_phone": f"eq.{from_phone}",
                "select":     "direction,body,timestamp",
                "order":      "timestamp.desc",
                "limit":      str(_HISTORY_LIMIT),
            })
            url = f"{os.getenv('SUPABASE_URL')}/rest/v1/wabiz_messages?{qs}"
            req = urllib.request.Request(url, headers={
                "apikey":        os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
                "Authorization": f"Bearer {os.getenv('SUPABASE_SERVICE_ROLE_KEY', '')}",
                "Accept":        "application/json",
            })
            with urllib.request.urlopen(req, timeout=10) as r:
                rows = json.loads(r.read().decode())
                return list(reversed(rows))
        except Exception:
            return []

    def _call_haiku(self, user_msg: str, history: list[dict], profile_name: str, empresa_id: str) -> str | None:
        messages = []
        for row in history:
            role    = "user" if row.get("direction") == "in" else "assistant"
            content = row.get("body") or ""
            if content:
                messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": user_msg})

        system_prompt = (
            f"Eres un asistente de WhatsApp para la empresa {empresa_id}. "
            f"Estás hablando con {profile_name}. "
            "Responde de forma concisa, amable y en el mismo idioma del usuario. "
            "Máximo 3 párrafos cortos."
        )

        payload = {
            "model":      "claude-haiku-4-5-20251001",
            "max_tokens": 512,
            "system":     system_prompt,
            "messages":   messages,
        }
        try:
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=json.dumps(payload).encode(),
                headers={
                    "content-type":      "application/json",
                    "x-api-key":         os.getenv("ANTHROPIC_API_KEY", ""),
                    "anthropic-version": "2023-06-01",
                    "User-Agent":        _UA,
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read().decode())
                return data["content"][0]["text"]
        except Exception:
            return None

    def _send_text(self, empresa_id: str, to: str, body: str) -> dict:
        try:
            import importlib.util
            from pathlib import Path
            svc_path = Path(__file__).parent.parent / "wabiz_send_text" / "service.py"
            spec = importlib.util.spec_from_file_location("wabiz_send_text_service", svc_path)
            mod  = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.WabizSendTextService().ejecutar({
                "empresa_id": empresa_id,
                "to":         to,
                "body":       body,
                "dry_run":    False,
            })
        except Exception as e:
            return {"ok": False, "error": str(e)}
