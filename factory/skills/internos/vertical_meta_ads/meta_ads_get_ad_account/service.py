"""Obtiene detalles completos de una cuenta publicitaria Meta Ads."""
from __future__ import annotations
import json, os, urllib.request, urllib.parse

_VERSION = "v24.0"
_UA = "FactoryFactory/0.1 (+https://github.com/)"


class MetaAdsGetAdAccountService:

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
            fields = (
                "id,name,account_status,currency,timezone_name,"
                "amount_spent,balance,daily_spend_limit,spend_cap,"
                "business,owner,created_time,disable_reason"
            )
            data = self._get(ad_account_id, {"fields": fields}, token)

            if "error" in data:
                err = data["error"]
                return {"ok": False, "error": err.get("message", str(err))}

            return {"ok": True, "data": data}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _get(self, path: str, params: dict, token: str) -> dict:
        params["access_token"] = token
        qs = urllib.parse.urlencode(params)
        url = f"https://graph.facebook.com/{_VERSION}/{path}?{qs}"
        req = urllib.request.Request(url, headers={"User-Agent": _UA})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
