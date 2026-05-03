"""Service for ig_post_carousel - publishes a multi-image carousel to Instagram via Meta Graph API."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request


class IgPostCarouselService:

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
        items = context.get("media_items")
        if not items or not isinstance(items, list):
            return False, "media_items es requerido y debe ser una lista"
        if len(items) < 2 or len(items) > 10:
            return False, "media_items debe tener entre 2 y 10 elementos"
        for i, item in enumerate(items):
            if not isinstance(item, dict):
                return False, f"media_items[{i}] debe ser un diccionario"
            if item.get("type") != "IMAGE":
                return False, f"media_items[{i}].type debe ser 'IMAGE'"
            url = item.get("url", "")
            if not url or not isinstance(url, str) or not url.startswith("http"):
                return False, f"media_items[{i}].url debe ser una URL publica valida"
        return True, None

    def _ejecutar(self, context: dict) -> dict:
        ig_user_id = self._ig_user_id(context)
        self._current_access_token = self._access_token(context)
        media_items = context["media_items"]
        caption = context.get("caption", "")

        try:
            child_ids = []
            for item in media_items:
                child = self._call_meta("POST", f"/{ig_user_id}/media", body={"is_carousel_item": True, "image_url": item["url"]})
                child_ids.append(child["id"])

            carousel_body: dict = {
                "media_type": "CAROUSEL",
                "children": ",".join(child_ids),
            }
            if caption:
                carousel_body["caption"] = caption
            carousel = self._call_meta("POST", f"/{ig_user_id}/media", body=carousel_body)
            carousel_id = carousel["id"]

            publish = self._call_meta("POST", f"/{ig_user_id}/media_publish", body={"creation_id": carousel_id})
            post_id = publish["id"]

            permalink_resp = self._call_meta("GET", f"/{post_id}", params={"fields": "permalink"})
            permalink = permalink_resp.get("permalink", "")

            return {"ok": True, "data": {"post_id": post_id, "permalink": permalink, "carousel_id": carousel_id, "child_count": len(child_ids)}}
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
