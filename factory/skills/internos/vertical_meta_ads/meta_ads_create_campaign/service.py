"""Crea una campaña en Meta Ads con objetivo, estado y categorías especiales."""
from __future__ import annotations
import json, os, urllib.request, urllib.parse

_VERSION = "v24.0"
_UA = "FactoryFactory/0.1 (+https://github.com/)"
_OBJECTIVES = {
    "OUTCOME_AWARENESS", "OUTCOME_TRAFFIC", "OUTCOME_ENGAGEMENT",
    "OUTCOME_LEADS", "OUTCOME_APP_PROMOTION", "OUTCOME_SALES",
}


class MetaAdsCreateCampaignService:

    def ejecutar(self, context: dict) -> dict:
        token = context.get("access_token") or os.getenv("META_ACCESS_TOKEN", "")
        ad_account_id = context.get("ad_account_id") or os.getenv("META_AD_ACCOUNT_ID", "")
        nombre = (context.get("nombre") or context.get("name") or "").strip()
        objetivo = (context.get("objetivo") or context.get("objective") or "").strip().upper()

        if not token:
            return {"ok": False, "error": "access_token requerido"}
        if not ad_account_id:
            return {"ok": False, "error": "ad_account_id requerido"}
        if not nombre:
            return {"ok": False, "error": "nombre requerido"}
        if not objetivo:
            return {"ok": False, "error": f"objetivo requerido. Valores: {sorted(_OBJECTIVES)}"}
        if objetivo not in _OBJECTIVES:
            return {"ok": False, "error": f"objetivo '{objetivo}' inválido. Valores: {sorted(_OBJECTIVES)}"}

        if not ad_account_id.startswith("act_"):
            ad_account_id = f"act_{ad_account_id}"

        estado = (context.get("estado") or context.get("status") or "PAUSED").upper()
        special_ad_categories = context.get("special_ad_categories") or []

        if context.get("dry_run", True):
            return {"ok": True, "data": {"dry_run": True, "nombre": nombre, "objetivo": objetivo, "estado": estado}}

        try:
            payload = {
                "name":                  nombre,
                "objective":             objetivo,
                "status":                estado,
                "special_ad_categories": json.dumps(special_ad_categories),
            }
            if context.get("daily_budget"):
                payload["daily_budget"] = str(int(float(context["daily_budget"]) * 100))
            if context.get("lifetime_budget"):
                payload["lifetime_budget"] = str(int(float(context["lifetime_budget"]) * 100))

            data = self._post(f"{ad_account_id}/campaigns", payload, token)

            if "error" in data:
                err = data["error"]
                return {"ok": False, "error": err.get("message", str(err))}

            return {"ok": True, "data": {"campaign_id": data.get("id"), "nombre": nombre, "objetivo": objetivo}}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _post(self, path: str, payload: dict, token: str) -> dict:
        payload["access_token"] = token
        data = urllib.parse.urlencode(payload).encode()
        url = f"https://graph.facebook.com/{_VERSION}/{path}"
        req = urllib.request.Request(url, data=data, headers={"User-Agent": _UA}, method="POST")
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
