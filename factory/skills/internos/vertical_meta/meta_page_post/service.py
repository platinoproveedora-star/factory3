"""Service for meta_page_post — publishes organic posts to a Facebook Page via Graph API."""
from __future__ import annotations

import calendar
import datetime as dt
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

_VALID_TIPOS = ("texto", "foto", "video")


class MetaPagePostService:

    def ejecutar(self, context: dict) -> dict:
        valido, error = self._validar(context)
        if not valido:
            return {"ok": False, "error": error}
        if context.get("dry_run", False):
            return {"ok": True, "message": "dry_run", "data": context}
        return self._ejecutar(context)

    def _validar(self, context: dict) -> tuple[bool, str | None]:
        fb_page_id = self._page_id(context)
        if not fb_page_id:
            return False, "fb_page_id es requerido en context o META_PAGE_ID en variables de entorno"
        tipo = (context.get("tipo_post") or "texto").strip().lower()
        if tipo not in _VALID_TIPOS:
            return False, f"tipo_post debe ser uno de: {', '.join(_VALID_TIPOS)}"
        mensaje = (context.get("mensaje") or "").strip()
        if not mensaje:
            return False, "mensaje es requerido"
        if tipo in ("foto", "video"):
            media_url = (context.get("media_url") or "").strip()
            if not media_url or not media_url.startswith("http"):
                return False, "media_url es requerido y debe ser una URL pública válida para tipo foto/video"
        if context.get("programar_para"):
            try:
                dt.datetime.fromisoformat(str(context["programar_para"]).replace("Z", "+00:00"))
            except ValueError:
                return False, "programar_para debe ser ISO 8601 (ej. 2025-12-31T18:00:00Z)"
        return True, None

    def _ejecutar(self, context: dict) -> dict:
        self._current_access_token = self._access_token(context)
        page_id = self._page_id(context)
        tipo = (context.get("tipo_post") or "texto").strip().lower()
        mensaje = context.get("mensaje", "").strip()
        media_url = (context.get("media_url") or "").strip()
        programar_para = context.get("programar_para")

        scheduled_ts = self._iso_to_unix(programar_para) if programar_para else None

        try:
            if tipo == "texto":
                return self._post_texto(page_id, mensaje, scheduled_ts)
            if tipo == "foto":
                return self._post_foto(page_id, media_url, mensaje, scheduled_ts)
            return self._post_video(page_id, media_url, mensaje, scheduled_ts, context)
        except urllib.error.HTTPError as exc:
            try:
                body = json.loads(exc.read().decode("utf-8"))
                msg = body.get("error", {}).get("message", str(exc))
            except Exception:
                msg = str(exc)
            return {"ok": False, "error": msg}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _post_texto(self, page_id: str, mensaje: str, scheduled_ts: int | None) -> dict:
        body: dict = {"message": mensaje}
        if scheduled_ts:
            body["published"] = False
            body["scheduled_publish_time"] = scheduled_ts
        resp = self._call_meta("POST", f"/{page_id}/feed", body=body)
        post_id = resp.get("id", "")
        permalink = self._get_permalink(post_id)
        return {"ok": True, "data": {"post_id": post_id, "permalink": permalink, "tipo": "texto"}}

    def _post_foto(self, page_id: str, url: str, caption: str, scheduled_ts: int | None) -> dict:
        body: dict = {"url": url, "caption": caption}
        if scheduled_ts:
            body["published"] = False
            body["scheduled_publish_time"] = scheduled_ts
        resp = self._call_meta("POST", f"/{page_id}/photos", body=body)
        post_id = resp.get("post_id") or resp.get("id", "")
        permalink = self._get_permalink(post_id) if post_id else ""
        return {"ok": True, "data": {"post_id": post_id, "permalink": permalink, "tipo": "foto"}}

    def _post_video(
        self,
        page_id: str,
        file_url: str,
        description: str,
        scheduled_ts: int | None,
        context: dict,
    ) -> dict:
        body: dict = {"file_url": file_url, "description": description}
        if scheduled_ts:
            body["scheduled_publish_time"] = scheduled_ts
            body["published"] = False
        resp = self._call_meta("POST", f"/{page_id}/videos", body=body)
        video_id = resp.get("id", "")

        max_wait = int(context.get("max_wait_seconds") or 120)
        start = time.time()
        while True:
            status_resp = self._call_meta("GET", f"/{video_id}", params={"fields": "status"})
            video_status = (status_resp.get("status") or {}).get("video_status", "processing")
            if video_status == "ready":
                break
            if video_status == "error":
                return {"ok": False, "error": f"Procesamiento de video falló: {status_resp}"}
            if time.time() - start >= max_wait:
                return {"ok": False, "error": f"Timeout: video no procesado en {max_wait}s (estado: {video_status})"}
            time.sleep(5)

        processing_seconds = int(time.time() - start)
        permalink = self._get_permalink(video_id)
        return {"ok": True, "data": {
            "post_id": video_id,
            "permalink": permalink,
            "tipo": "video",
            "processing_seconds": processing_seconds,
        }}

    def _get_permalink(self, post_id: str) -> str:
        try:
            resp = self._call_meta("GET", f"/{post_id}", params={"fields": "permalink_url,permalink"})
            return resp.get("permalink_url") or resp.get("permalink") or ""
        except Exception:
            return ""

    def _call_meta(self, method: str, path: str, params: dict | None = None, body: dict | None = None) -> dict:
        access_token = (
            getattr(self, "_current_access_token", None)
            or os.getenv("META_PAGE_ACCESS_TOKEN")
            or os.getenv("META_ACCESS_TOKEN")
        )
        if not access_token:
            raise ValueError("META_ACCESS_TOKEN no configurada")
        graph_version = os.getenv("META_GRAPH_API_VERSION", "v24.0")
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
                headers={"Content-Type": "application/json"},
                method=method.upper(),
            )
        req.add_header("User-Agent", "FactoryFactory/0.1 (+https://github.com/)")
        with urllib.request.urlopen(req, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))

    def _connection(self, context: dict) -> dict:
        conn = context.get("connection")
        return conn if isinstance(conn, dict) else {}

    def _page_id(self, context: dict) -> str | None:
        return (
            context.get("fb_page_id")
            or self._connection(context).get("page_id")
            or os.getenv("META_PAGE_ID")
        )

    def _access_token(self, context: dict) -> str | None:
        return (
            context.get("access_token")
            or self._connection(context).get("access_token")
            or os.getenv("META_PAGE_ACCESS_TOKEN")
            or os.getenv("META_ACCESS_TOKEN")
        )

    def _iso_to_unix(self, iso_str: str) -> int:
        parsed = dt.datetime.fromisoformat(str(iso_str).replace("Z", "+00:00"))
        return int(calendar.timegm(parsed.utctimetuple()))
