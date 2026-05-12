"""Service for ig_reply_comment - replies to an Instagram comment via Meta Graph API."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request


class IgReplyCommentService:

    def ejecutar(self, context: dict) -> dict:
        valido, error = self._validar(context)
        if not valido:
            return {"ok": False, "error": error}
        if context.get("dry_run", False):
            return {"ok": True, "message": "dry_run", "data": context}
        return self._ejecutar(context)

    def _validar(self, context: dict) -> tuple[bool, str | None]:
        if not context.get("comment_id") or not isinstance(context["comment_id"], str):
            return False, "comment_id es requerido y debe ser texto"
        message = context.get("message")
        if not message or not isinstance(message, str):
            return False, "message es requerido y debe ser texto"
        if len(message) > 2200:
            return False, "message no puede superar 2200 caracteres"
        return True, None

    def _ejecutar(self, context: dict) -> dict:
        comment_id = context["comment_id"]
        message = context["message"]

        access_token = self._access_token(context)
        if not access_token:
            return {"ok": False, "error": "IG_ACCESS_TOKEN no configurada"}

        body = {"message": message, "access_token": access_token}
        graph_version = os.getenv("IG_GRAPH_API_VERSION", "v24.0")
        url = f"https://graph.facebook.com/{graph_version}/{comment_id}/replies"

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(body).encode("utf-8"),
                headers={"content-type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode("utf-8"))
            return {"ok": True, "data": {"reply_id": result.get("id", ""), "comment_id": comment_id}}
        except urllib.error.HTTPError as exc:
            try:
                err_body = json.loads(exc.read().decode("utf-8"))
                msg = err_body.get("error", {}).get("message", str(exc))
            except Exception:
                msg = str(exc)
            return {"ok": False, "error": msg}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _connection(self, context: dict) -> dict:
        connection = context.get("connection")
        return connection if isinstance(connection, dict) else {}

    def _access_token(self, context: dict) -> str | None:
        return context.get("access_token") or self._connection(context).get("access_token") or os.getenv("IG_ACCESS_TOKEN") or os.getenv("META_ACCESS_TOKEN")
