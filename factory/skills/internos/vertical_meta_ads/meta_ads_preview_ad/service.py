"""Genera preview HTML de un anuncio en el formato de placement solicitado."""
from __future__ import annotations
import json, os, urllib.request, urllib.parse

_VERSION = "v24.0"
_UA = "FactoryFactory/0.1 (+https://github.com/)"
_FORMATS = {
    "DESKTOP_FEED_STANDARD", "MOBILE_FEED_STANDARD", "MOBILE_FEED_BASIC",
    "INSTAGRAM_STANDARD", "INSTAGRAM_STORY", "MARKETPLACE",
    "RIGHT_COLUMN_STANDARD", "AUDIENCE_NETWORK_OUTSTREAM_VIDEO",
}


class MetaAdsPreviewAdService:

    def ejecutar(self, context: dict) -> dict:
        token = context.get("access_token") or os.getenv("META_ACCESS_TOKEN", "")
        ad_id = (context.get("ad_id") or "").strip()

        if not token:
            return {"ok": False, "error": "access_token requerido"}
        if not ad_id:
            return {"ok": False, "error": "ad_id requerido"}

        ad_format = (context.get("ad_format") or "MOBILE_FEED_STANDARD").upper()
        if ad_format not in _FORMATS:
            ad_format = "MOBILE_FEED_STANDARD"

        try:
            data = self._get(f"{ad_id}/previews", {"ad_format": ad_format}, token)
            if "error" in data:
                err = data["error"]
                return {"ok": False, "error": err.get("message", str(err))}

            previews = data.get("data", [])
            iframe = previews[0].get("body") if previews else None

            return {"ok": True, "data": {
                "ad_id":     ad_id,
                "ad_format": ad_format,
                "iframe":    iframe,
                "total":     len(previews),
            }}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _get(self, path: str, params: dict, token: str) -> dict:
        params["access_token"] = token
        qs = urllib.parse.urlencode(params)
        url = f"https://graph.facebook.com/{_VERSION}/{path}?{qs}"
        req = urllib.request.Request(url, headers={"User-Agent": _UA})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
