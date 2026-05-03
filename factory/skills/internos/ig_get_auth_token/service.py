"""Service for ig_get_auth_token - exchanges a short-lived Meta token for a long-lived one (60 days)."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request


class IgGetAuthTokenService:

    def ejecutar(self, context: dict) -> dict:
        valido, error = self._validar(context)
        if not valido:
            return {"ok": False, "error": error}
        if context.get("dry_run", False):
            return {"ok": True, "message": "dry_run", "data": context}
        return self._ejecutar(context)

    def _validar(self, context: dict) -> tuple[bool, str | None]:
        for field in ("short_lived_token", "app_id", "app_secret"):
            if not context.get(field) or not isinstance(context[field], str):
                return False, f"{field} es requerido y debe ser texto"
        return True, None

    def _ejecutar(self, context: dict) -> dict:
        short_lived_token = context["short_lived_token"]
        app_id = context["app_id"]
        app_secret = context["app_secret"]

        params = {
            "grant_type": "fb_exchange_token",
            "client_id": app_id,
            "client_secret": app_secret,
            "fb_exchange_token": short_lived_token,
        }
        graph_version = os.getenv("IG_GRAPH_API_VERSION", "v24.0")
        url = f"https://graph.facebook.com/{graph_version}/oauth/access_token?" + urllib.parse.urlencode(params)

        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode("utf-8"))
            expires_in = result.get("expires_in", 0)
            return {
                "ok": True,
                "data": {
                    "access_token": result.get("access_token", ""),
                    "token_type": result.get("token_type", "bearer"),
                    "expires_in": expires_in,
                    "expires_in_days": expires_in // 86400,
                },
            }
        except urllib.error.HTTPError as exc:
            try:
                body = json.loads(exc.read().decode("utf-8"))
                msg = body.get("error", {}).get("message", str(exc))
            except Exception:
                msg = str(exc)
            return {"ok": False, "error": msg}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
