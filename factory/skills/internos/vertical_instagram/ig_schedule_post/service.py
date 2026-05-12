"""Service for ig_schedule_post - schedules an Instagram post for a future date via Meta Graph API."""
from __future__ import annotations

import datetime
import json
import os
import urllib.error
import urllib.parse
import urllib.request


class IgSchedulePostService:

    def ejecutar(self, context: dict) -> dict:
        valido, error = self._validar(context)
        if not valido:
            return {"ok": False, "error": error}
        if context.get("dry_run", False):
            return {"ok": True, "message": "dry_run", "data": context}
        return self._ejecutar(context)

    def _validar(self, context: dict) -> tuple[bool, str | None]:
        ig_user_id = self._ig_user_id(context)
        if not ig_user_id or not isinstance(ig_user_id, str):
            return False, "ig_user_id es requerido en context o IG_BUSINESS_ACCOUNT_ID en variables de entorno"
        image_url = context.get("image_url")
        if not image_url or not isinstance(image_url, str) or not image_url.startswith("http"):
            return False, "image_url es requerido y debe ser una URL publica valida"
        scheduled_datetime = context.get("scheduled_datetime")
        if not scheduled_datetime or not isinstance(scheduled_datetime, str):
            return False, "scheduled_datetime es requerido en formato ISO 8601 (YYYY-MM-DDTHH:MM:SS)"
        try:
            dt = datetime.datetime.fromisoformat(scheduled_datetime)
            now = datetime.datetime.now(dt.tzinfo) if dt.tzinfo else datetime.datetime.now()
            min_future = now + datetime.timedelta(minutes=10)
            max_future = now + datetime.timedelta(days=75)
            if dt < min_future:
                return False, "scheduled_datetime debe ser al menos 10 minutos en el futuro"
            if dt > max_future:
                return False, "scheduled_datetime no puede estar a mas de 75 dias en el futuro"
        except ValueError:
            return False, "scheduled_datetime debe estar en formato ISO 8601 (YYYY-MM-DDTHH:MM:SS)"
        return True, None

    def _ejecutar(self, context: dict) -> dict:
        ig_user_id = self._ig_user_id(context)
        self._current_access_token = self._access_token(context)
        image_url = context["image_url"]
        caption = context.get("caption", "")
        alt_text = context.get("alt_text", "")
        scheduled_datetime = context["scheduled_datetime"]

        dt = datetime.datetime.fromisoformat(scheduled_datetime)
        unix_ts = int(dt.timestamp())

        try:
            container_body: dict = {
                "image_url": image_url,
                "published": False,
                "scheduled_publish_time": unix_ts,
            }
            if caption:
                container_body["caption"] = caption
            if alt_text:
                container_body["alt_text"] = alt_text
            container = self._call_meta("POST", f"/{ig_user_id}/media", body=container_body)
            creation_id = container["id"]

            publish = self._call_meta("POST", f"/{ig_user_id}/media_publish", body={"creation_id": creation_id})
            post_id = publish["id"]

            return {"ok": True, "data": {"post_id": post_id, "creation_id": creation_id, "scheduled_unix": unix_ts, "scheduled_iso": scheduled_datetime}}
        except urllib.error.HTTPError as exc:
            try:
                body = json.loads(exc.read().decode("utf-8"))
                msg = body.get("error", {}).get("message", str(exc))
            except Exception:
                msg = str(exc)
            return {"ok": False, "error": msg}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _call_meta(self, method: str, path: str, params: dict | None = None, body: dict | None = None) -> dict:
        access_token = getattr(self, "_current_access_token", None) or os.getenv("IG_ACCESS_TOKEN") or os.getenv("META_ACCESS_TOKEN")
        if not access_token:
            raise ValueError("IG_ACCESS_TOKEN no configurada")
        graph_version = os.getenv("IG_GRAPH_API_VERSION", "v24.0")
        base_url = f"https://graph.facebook.com/{graph_version}{path}"
        if method.upper() == "GET":
            query = {"access_token": access_token}
            if params:
                query.update(params)
            url = base_url + "?" + urllib.parse.urlencode(query)
            req = urllib.request.Request(url, method="GET")
        else:
            data = dict(body or {})
            data["access_token"] = access_token
            req = urllib.request.Request(
                base_url,
                data=json.dumps(data).encode("utf-8"),
                headers={"content-type": "application/json"},
                method=method.upper(),
            )
        with urllib.request.urlopen(req, timeout=45) as response:
            return json.loads(response.read().decode("utf-8"))

    def _connection(self, context: dict) -> dict:
        connection = context.get("connection")
        return connection if isinstance(connection, dict) else {}

    def _ig_user_id(self, context: dict) -> str | None:
        return context.get("ig_user_id") or self._connection(context).get("ig_user_id") or os.getenv("IG_BUSINESS_ACCOUNT_ID")

    def _access_token(self, context: dict) -> str | None:
        return context.get("access_token") or self._connection(context).get("access_token") or os.getenv("IG_ACCESS_TOKEN") or os.getenv("META_ACCESS_TOKEN")
