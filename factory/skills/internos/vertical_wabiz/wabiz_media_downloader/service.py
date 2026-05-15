"""Descarga archivo media de WhatsApp Cloud API y devuelve bytes en base64."""
from __future__ import annotations
import base64
import json
import os
import urllib.parse
import urllib.request

_GRAPH_BASE = "https://graph.facebook.com"
_UA         = "FactoryFactory/0.1 (+https://github.com/)"


class WabizMediaDownloaderService:

    def ejecutar(self, context: dict) -> dict:
        media_id   = context.get("media_id")
        empresa_id = context.get("empresa_id")

        if not media_id:
            return {"ok": False, "error": "media_id requerido"}
        if not empresa_id:
            return {"ok": False, "error": "empresa_id requerido"}

        token, version = self._load_credentials(empresa_id)
        if not token:
            return {"ok": False, "error": f"Sin config para empresa_id={empresa_id}"}

        meta = self._get_media_meta(media_id, token, version)
        if not meta.get("ok"):
            return meta

        media_url = meta["data"].get("url", "")
        mime_type = meta["data"].get("mime_type", "application/octet-stream")
        sha256    = meta["data"].get("sha256", "")
        file_size = meta["data"].get("file_size", 0)

        dl = self._download_media(media_url, token)
        if not dl.get("ok"):
            return dl

        raw_bytes   = dl["bytes"]
        content_b64 = base64.b64encode(raw_bytes).decode()

        return {"ok": True, "data": {
            "content_b64": content_b64,
            "mime_type":   mime_type,
            "media_id":    media_id,
            "size_bytes":  file_size or len(raw_bytes),
            "sha256":      sha256,
        }}

    def _load_credentials(self, empresa_id: str) -> tuple[str, str]:
        try:
            qs  = urllib.parse.urlencode({
                "empresa_id": f"eq.{empresa_id}",
                "select":     "access_token,graph_version",
                "limit":      "1",
            })
            url = f"{os.getenv('SUPABASE_URL', '').rstrip('/')}/rest/v1/wabiz_config?{qs}"
            key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
            req = urllib.request.Request(url, headers={
                "apikey":        key,
                "Authorization": f"Bearer {key}",
                "Accept":        "application/json",
                "User-Agent":    _UA,
            })
            with urllib.request.urlopen(req, timeout=10) as r:
                rows = json.loads(r.read().decode())
                if rows:
                    return rows[0]["access_token"], rows[0].get("graph_version", "v24.0")
        except Exception:
            pass
        return "", "v24.0"

    def _get_media_meta(self, media_id: str, token: str, version: str) -> dict:
        url = f"{_GRAPH_BASE}/{version}/{media_id}"
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {token}",
            "User-Agent":    _UA,
        })
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read().decode())
                return {"ok": True, "data": data}
        except Exception as e:
            return {"ok": False, "error": f"Error obteniendo metadata de media: {e}"}

    def _download_media(self, url: str, token: str) -> dict:
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {token}",
            "User-Agent":    _UA,
        })
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return {"ok": True, "bytes": r.read()}
        except Exception as e:
            return {"ok": False, "error": f"Error descargando media: {e}"}
