"""Service for ig_post_reel - publishes a Reel to Instagram via Meta Graph API with polling."""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request


class IgPostReelService:

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
        video_url = context.get("video_url")
        if not video_url or not isinstance(video_url, str):
            return False, "video_url es requerido y debe ser texto"
        if not video_url.startswith("http"):
            return False, "video_url debe ser una URL publica valida"
        share_to_feed = context.get("share_to_feed")
        if share_to_feed is not None and not isinstance(share_to_feed, bool):
            return False, "share_to_feed debe ser booleano"
        max_wait = context.get("max_wait_seconds")
        if max_wait is not None and (not isinstance(max_wait, int) or max_wait < 60 or max_wait > 300):
            return False, "max_wait_seconds debe ser un entero entre 60 y 300"
        return True, None

    def _ejecutar(self, context: dict) -> dict:
        ig_user_id = self._ig_user_id(context)
        self._current_access_token = self._access_token(context)
        video_url = context["video_url"]
        caption = context.get("caption", "")
        share_to_feed = context.get("share_to_feed", True)
        max_wait = context.get("max_wait_seconds", 120)

        try:
            container_body: dict = {
                "media_type": "REELS",
                "video_url": video_url,
                "share_to_feed": share_to_feed,
            }
            if caption:
                container_body["caption"] = caption
            container = self._call_meta("POST", f"/{ig_user_id}/media", body=container_body)
            creation_id = container["id"]

            start = time.time()
            while True:
                status_resp = self._call_meta("GET", f"/{creation_id}", params={"fields": "status_code"})
                status_code = status_resp.get("status_code", "IN_PROGRESS")
                if status_code == "FINISHED":
                    break
                if status_code in ("ERROR", "EXPIRED"):
                    return {"ok": False, "error": f"Procesamiento de video fallo: {status_code}"}
                elapsed = time.time() - start
                if elapsed >= max_wait:
                    return {"ok": False, "error": f"Timeout: el video no termino de procesarse en {max_wait}s"}
                time.sleep(5)

            processing_seconds = int(time.time() - start)
            publish = self._call_meta("POST", f"/{ig_user_id}/media_publish", body={"creation_id": creation_id})
            post_id = publish["id"]

            permalink_resp = self._call_meta("GET", f"/{post_id}", params={"fields": "permalink"})
            permalink = permalink_resp.get("permalink", "")

            return {"ok": True, "data": {"post_id": post_id, "permalink": permalink, "creation_id": creation_id, "processing_seconds": processing_seconds}}
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
        with urllib.request.urlopen(req, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))

    def _connection(self, context: dict) -> dict:
        connection = context.get("connection")
        return connection if isinstance(connection, dict) else {}

    def _ig_user_id(self, context: dict) -> str | None:
        return context.get("ig_user_id") or self._connection(context).get("ig_user_id") or os.getenv("IG_BUSINESS_ACCOUNT_ID")

    def _access_token(self, context: dict) -> str | None:
        return context.get("access_token") or self._connection(context).get("access_token") or os.getenv("IG_ACCESS_TOKEN") or os.getenv("META_ACCESS_TOKEN")
