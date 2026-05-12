"""Crea un conjunto de anuncios con targeting, presupuesto, optimización y calendario."""
from __future__ import annotations
import json, os, urllib.request, urllib.parse

_VERSION = "v24.0"
_UA = "FactoryFactory/0.1 (+https://github.com/)"
_BILLING_EVENTS = {"IMPRESSIONS", "LINK_CLICKS", "APP_INSTALLS", "NONE", "PAGE_LIKES", "POST_ENGAGEMENT", "THRUPLAY", "PURCHASE", "LISTING_INTERACTION"}
_OPT_GOALS = {"REACH", "IMPRESSIONS", "LINK_CLICKS", "LANDING_PAGE_VIEWS", "LEAD_GENERATION", "CONVERSIONS", "APP_INSTALLS", "THRUPLAY", "VALUE", "OFFSITE_CONVERSIONS"}


class MetaAdsCreateAdsetService:

    def ejecutar(self, context: dict) -> dict:
        token = context.get("access_token") or os.getenv("META_ACCESS_TOKEN", "")
        ad_account_id = context.get("ad_account_id") or os.getenv("META_AD_ACCOUNT_ID", "")
        campaign_id = (context.get("campaign_id") or "").strip()
        nombre = (context.get("nombre") or context.get("name") or "").strip()
        billing_event = (context.get("billing_event") or "IMPRESSIONS").upper()
        optimization_goal = (context.get("optimization_goal") or "REACH").upper()
        daily_budget = context.get("daily_budget")
        targeting = context.get("targeting") or {}

        if not token:
            return {"ok": False, "error": "access_token requerido"}
        if not ad_account_id:
            return {"ok": False, "error": "ad_account_id requerido"}
        if not campaign_id:
            return {"ok": False, "error": "campaign_id requerido"}
        if not nombre:
            return {"ok": False, "error": "nombre requerido"}
        if not daily_budget and not context.get("lifetime_budget"):
            return {"ok": False, "error": "daily_budget o lifetime_budget requerido (en pesos, ej. 100)"}

        if not ad_account_id.startswith("act_"):
            ad_account_id = f"act_{ad_account_id}"

        if context.get("dry_run", True):
            return {"ok": True, "data": {"dry_run": True, "nombre": nombre, "campaign_id": campaign_id, "optimization_goal": optimization_goal}}

        try:
            payload = {
                "name":              nombre,
                "campaign_id":       campaign_id,
                "billing_event":     billing_event,
                "optimization_goal": optimization_goal,
                "targeting":         json.dumps(targeting) if targeting else json.dumps({"geo_locations": {"countries": ["MX"]}}),
                "status":            (context.get("estado") or context.get("status") or "PAUSED").upper(),
            }
            if daily_budget:
                payload["daily_budget"] = str(int(float(daily_budget) * 100))
            if context.get("lifetime_budget"):
                payload["lifetime_budget"] = str(int(float(context["lifetime_budget"]) * 100))
            if context.get("bid_amount"):
                payload["bid_amount"] = str(int(float(context["bid_amount"]) * 100))
            if context.get("start_time"):
                payload["start_time"] = context["start_time"]
            if context.get("end_time"):
                payload["end_time"] = context["end_time"]

            data = self._post(f"{ad_account_id}/adsets", payload, token)
            if "error" in data:
                err = data["error"]
                return {"ok": False, "error": err.get("message", str(err))}

            return {"ok": True, "data": {"adset_id": data.get("id"), "nombre": nombre}}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _post(self, path: str, payload: dict, token: str) -> dict:
        payload["access_token"] = token
        data = urllib.parse.urlencode(payload).encode()
        url = f"https://graph.facebook.com/{_VERSION}/{path}"
        req = urllib.request.Request(url, data=data, headers={"User-Agent": _UA}, method="POST")
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
