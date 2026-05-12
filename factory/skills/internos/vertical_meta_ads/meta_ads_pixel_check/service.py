"""Lista pixels instalados en la cuenta publicitaria y verifica su último disparo."""
from __future__ import annotations
import json, os, urllib.request, urllib.parse

_VERSION = "v24.0"
_UA = "FactoryFactory/0.1 (+https://github.com/)"


class MetaAdsPixelCheckService:

    def ejecutar(self, context: dict) -> dict:
        token = context.get("access_token") or os.getenv("META_ACCESS_TOKEN", "")
        ad_account_id = context.get("ad_account_id") or os.getenv("META_AD_ACCOUNT_ID", "")

        if not token:
            return {"ok": False, "error": "access_token requerido"}
        if not ad_account_id:
            return {"ok": False, "error": "ad_account_id requerido"}

        if not ad_account_id.startswith("act_"):
            ad_account_id = f"act_{ad_account_id}"

        try:
            fields = "id,name,last_fired_time,is_unavailable,code,owner_business"
            data = self._get(f"{ad_account_id}/adspixels", {"fields": fields}, token)

            if "error" in data:
                err = data["error"]
                return {"ok": False, "error": err.get("message", str(err))}

            pixels = data.get("data", [])
            tiene_pixel = len(pixels) > 0
            activos = [p for p in pixels if not p.get("is_unavailable", False)]

            return {"ok": True, "data": {
                "tiene_pixel":   tiene_pixel,
                "total":         len(pixels),
                "activos":       len(activos),
                "pixels":        pixels,
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
