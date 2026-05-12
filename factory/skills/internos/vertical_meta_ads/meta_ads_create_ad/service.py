"""Crea un anuncio vinculando conjunto de anuncios y creativo."""
from __future__ import annotations
import json, os, urllib.request, urllib.parse

_VERSION = "v24.0"
_UA = "FactoryFactory/0.1 (+https://github.com/)"


class MetaAdsCreateAdService:

    def ejecutar(self, context: dict) -> dict:
        token = context.get("access_token") or os.getenv("META_ACCESS_TOKEN", "")
        ad_account_id = context.get("ad_account_id") or os.getenv("META_AD_ACCOUNT_ID", "")
        adset_id = (context.get("adset_id") or "").strip()
        creative_id = (context.get("creative_id") or "").strip()
        nombre = (context.get("nombre") or context.get("name") or "").strip()

        if not token:
            return {"ok": False, "error": "access_token requerido"}
        if not ad_account_id:
            return {"ok": False, "error": "ad_account_id requerido"}
        if not adset_id:
            return {"ok": False, "error": "adset_id requerido"}
        if not creative_id:
            return {"ok": False, "error": "creative_id requerido"}
        if not nombre:
            return {"ok": False, "error": "nombre requerido"}

        if not ad_account_id.startswith("act_"):
            ad_account_id = f"act_{ad_account_id}"

        estado = (context.get("estado") or context.get("status") or "PAUSED").upper()

        if context.get("dry_run", True):
            return {"ok": True, "data": {"dry_run": True, "nombre": nombre, "adset_id": adset_id, "creative_id": creative_id}}

        try:
            payload = {
                "name":     nombre,
                "adset_id": adset_id,
                "creative": json.dumps({"creative_id": creative_id}),
                "status":   estado,
            }
            data = self._post(f"{ad_account_id}/ads", payload, token)
            if "error" in data:
                err = data["error"]
                return {"ok": False, "error": err.get("message", str(err))}

            return {"ok": True, "data": {"ad_id": data.get("id"), "nombre": nombre, "estado": estado}}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _post(self, path: str, payload: dict, token: str) -> dict:
        payload["access_token"] = token
        data = urllib.parse.urlencode(payload).encode()
        url = f"https://graph.facebook.com/{_VERSION}/{path}"
        req = urllib.request.Request(url, data=data, headers={"User-Agent": _UA}, method="POST")
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
