"""Obtiene métricas de performance (impresiones, clics, gasto, ROAS, acciones) por nivel y período."""
from __future__ import annotations
import json, os, urllib.request, urllib.parse

_VERSION = "v24.0"
_UA = "FactoryFactory/0.1 (+https://github.com/)"
_DATE_PRESETS = {
    "today", "yesterday", "this_week_sun_today", "last_week_sun_sat",
    "last_7d", "last_14d", "last_28d", "last_30d", "last_90d",
    "this_month", "last_month", "this_quarter", "last_year",
}
_LEVELS = {"ad", "adset", "campaign", "account"}
_DEFAULT_FIELDS = (
    "impressions,clicks,spend,ctr,cpc,cpm,reach,frequency,"
    "actions,cost_per_action_type,action_values,purchase_roas"
)


class MetaAdsGetInsightsService:

    def ejecutar(self, context: dict) -> dict:
        token = context.get("access_token") or os.getenv("META_ACCESS_TOKEN", "")
        object_id = (context.get("object_id") or context.get("ad_account_id") or os.getenv("META_AD_ACCOUNT_ID", "")).strip()

        if not token:
            return {"ok": False, "error": "access_token requerido"}
        if not object_id:
            return {"ok": False, "error": "object_id requerido (ad_account_id, campaign_id, adset_id o ad_id)"}

        if object_id and not object_id.startswith("act_") and len(object_id) < 10:
            object_id = f"act_{object_id}"

        date_preset = context.get("date_preset", "last_7d")
        if date_preset not in _DATE_PRESETS:
            date_preset = "last_7d"

        level = context.get("level", "campaign")
        if level not in _LEVELS:
            level = "campaign"

        fields = context.get("fields") or _DEFAULT_FIELDS
        breakdowns = context.get("breakdowns") or ""

        try:
            params: dict = {
                "fields":      fields,
                "date_preset": date_preset,
                "level":       level,
                "limit":       str(context.get("limit", 25)),
            }
            if breakdowns:
                params["breakdowns"] = breakdowns

            data = self._get(f"{object_id}/insights", params, token)
            if "error" in data:
                err = data["error"]
                return {"ok": False, "error": err.get("message", str(err))}

            rows = data.get("data", [])
            return {"ok": True, "data": {
                "total":       len(rows),
                "date_preset": date_preset,
                "level":       level,
                "insights":    rows,
            }}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _get(self, path: str, params: dict, token: str) -> dict:
        params["access_token"] = token
        qs = urllib.parse.urlencode(params)
        url = f"https://graph.facebook.com/{_VERSION}/{path}?{qs}"
        req = urllib.request.Request(url, headers={"User-Agent": _UA})
        with urllib.request.urlopen(req, timeout=45) as r:
            return json.loads(r.read().decode())
