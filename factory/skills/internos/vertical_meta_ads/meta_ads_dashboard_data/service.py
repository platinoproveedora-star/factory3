"""Devuelve campañas activas con gasto, impresiones y clics para el dashboard."""
from __future__ import annotations
import json, os, urllib.request, urllib.parse

_VERSION = "v24.0"
_UA = "FactoryFactory/0.1 (+https://github.com/)"


class MetaAdsDashboardDataService:

    def ejecutar(self, context: dict) -> dict:
        token = context.get("access_token") or os.getenv("META_ACCESS_TOKEN", "")
        ad_account_id = context.get("ad_account_id") or os.getenv("META_AD_ACCOUNT_ID", "")

        if not token:
            return {"ok": False, "error": "access_token requerido"}
        if not ad_account_id:
            return {"ok": False, "error": "ad_account_id requerido"}

        if not ad_account_id.startswith("act_"):
            ad_account_id = f"act_{ad_account_id}"

        date_preset = context.get("date_preset", "last_7d")

        try:
            # Campañas activas/pausadas
            filtering = json.dumps([{"field": "effective_status", "operator": "IN", "value": ["ACTIVE", "PAUSED"]}])
            camp_fields = "id,name,status,objective,daily_budget,lifetime_budget,created_time"
            campaigns_data = self._get(f"{ad_account_id}/campaigns", {
                "fields":    camp_fields,
                "filtering": filtering,
                "limit":     "50",
            }, token)

            campaigns = campaigns_data.get("data", [])

            # Insights globales de cuenta
            insights_data = self._get(f"{ad_account_id}/insights", {
                "fields":      "impressions,clicks,spend,ctr,cpc,reach,actions",
                "date_preset": date_preset,
                "level":       "account",
            }, token)

            insights = insights_data.get("data", [{}])
            resumen = insights[0] if insights else {}

            return {"ok": True, "data": {
                "ad_account_id":  ad_account_id,
                "date_preset":    date_preset,
                "total_campanas": len(campaigns),
                "campanas":       campaigns,
                "resumen_cuenta": {
                    "impresiones": resumen.get("impressions", "0"),
                    "clics":       resumen.get("clicks", "0"),
                    "gasto":       resumen.get("spend", "0"),
                    "ctr":         resumen.get("ctr", "0"),
                    "cpc":         resumen.get("cpc", "0"),
                    "alcance":     resumen.get("reach", "0"),
                },
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
