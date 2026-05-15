from __future__ import annotations
import json, os, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone

_VERSION = "v24.0"
_UA = "FactoryFactory/0.1 (+https://github.com/)"


class MetaAdsLeadCampaignFlowService:

    def ejecutar(self, context: dict) -> dict:
        token = (context.get("access_token") or os.getenv("META_ACCESS_TOKEN") or "").strip()
        ad_account_id = (context.get("ad_account_id") or os.getenv("META_AD_ACCOUNT_ID") or "").strip()
        page_id = (context.get("page_id") or os.getenv("META_PAGE_ID") or os.getenv("IG_PAGE_ID") or "").strip()
        form_id = (context.get("form_id") or "").strip()

        if not token:
            return {"ok": False, "error": "access_token requerido (META_ACCESS_TOKEN)"}
        if not ad_account_id:
            return {"ok": False, "error": "ad_account_id requerido (META_AD_ACCOUNT_ID)"}
        if not page_id:
            return {"ok": False, "error": "page_id requerido (META_PAGE_ID o IG_PAGE_ID)"}
        if not form_id:
            return {"ok": False, "error": "form_id requerido. Crea primero vertical_meta_ads/meta_lead_form_create"}
        if not ad_account_id.startswith("act_"):
            ad_account_id = f"act_{ad_account_id}"

        campaign_name = (context.get("campaign_name") or context.get("nombre_campana") or "").strip()
        message = (context.get("message") or context.get("mensaje") or "").strip()
        title = (context.get("title") or context.get("titulo") or "").strip()
        description = (context.get("description") or context.get("descripcion") or "").strip()

        if not campaign_name:
            return {"ok": False, "error": "campaign_name requerido"}
        if not message:
            return {"ok": False, "error": "message requerido"}
        if not title:
            return {"ok": False, "error": "title requerido"}

        daily_budget = float(context.get("daily_budget") or context.get("presupuesto_diario") or 0)
        if daily_budget <= 0:
            return {"ok": False, "error": "daily_budget requerido y debe ser mayor a 0"}

        days = int(context.get("days") or context.get("dias") or 7)
        status = (context.get("status") or context.get("estado") or "PAUSED").upper()
        if status != "PAUSED" and not context.get("allow_active"):
            return {"ok": False, "error": "Por seguridad este flujo crea en PAUSED. Usa allow_active=true para otro estado."}

        targeting = context.get("targeting") or {"geo_locations": {"countries": ["MX"]}}
        special_ad_categories = context.get("special_ad_categories") or []

        if context.get("dry_run", True):
            return {"ok": True, "data": {
                "dry_run": True,
                "campaign_name": campaign_name,
                "form_id": form_id,
                "page_id": page_id,
                "ad_account_id": ad_account_id,
                "daily_budget": daily_budget,
                "days": days,
                "status": status,
                "targeting": targeting,
                "special_ad_categories": special_ad_categories,
                "pasos": ["campaign", "adset", "creative_lead_form", "ad"],
            }}

        resultado = {"pasos": []}
        try:
            campaign = self._post(f"{ad_account_id}/campaigns", {
                "name": campaign_name,
                "objective": "OUTCOME_LEADS",
                "status": status,
                "special_ad_categories": json.dumps(special_ad_categories),
            }, token)
            if "error" in campaign:
                return self._fail("campaign", campaign, resultado)
            campaign_id = campaign["id"]
            resultado["campaign_id"] = campaign_id
            resultado["pasos"].append("campaign_creada")

            adset = self._post(f"{ad_account_id}/adsets", {
                "name": context.get("adset_name") or f"{campaign_name} - Adset",
                "campaign_id": campaign_id,
                "billing_event": (context.get("billing_event") or "IMPRESSIONS").upper(),
                "optimization_goal": (context.get("optimization_goal") or "LEAD_GENERATION").upper(),
                "daily_budget": str(int(daily_budget * 100)),
                "targeting": json.dumps(targeting),
                "promoted_object": json.dumps(context.get("promoted_object") or {"page_id": page_id}),
                "end_time": self._end_time(days),
                "status": status,
            }, token)
            if "error" in adset:
                return self._fail("adset", adset, resultado)
            adset_id = adset["id"]
            resultado["adset_id"] = adset_id
            resultado["pasos"].append("adset_creado")

            link_data = {
                "message": message,
                "name": title,
                "call_to_action": {"type": (context.get("cta_type") or "SIGN_UP").upper(), "value": {"lead_gen_form_id": form_id}},
            }
            if description:
                link_data["description"] = description
            if context.get("image_url"):
                link_data["picture"] = context["image_url"]
            if context.get("link"):
                link_data["link"] = context["link"]

            creative = self._post(f"{ad_account_id}/adcreatives", {
                "name": context.get("creative_name") or f"{campaign_name} - Creative",
                "object_story_spec": json.dumps({"page_id": page_id, "link_data": link_data}),
            }, token)
            if "error" in creative:
                return self._fail("creative", creative, resultado)
            creative_id = creative["id"]
            resultado["creative_id"] = creative_id
            resultado["pasos"].append("creative_creado")

            ad = self._post(f"{ad_account_id}/ads", {
                "name": context.get("ad_name") or f"{campaign_name} - Ad",
                "adset_id": adset_id,
                "creative": json.dumps({"creative_id": creative_id}),
                "status": status,
            }, token)
            if "error" in ad:
                return self._fail("ad", ad, resultado)
            resultado["ad_id"] = ad["id"]
            resultado["pasos"].append("ad_creado")

            resultado.update({"estado": status, "form_id": form_id, "daily_budget": daily_budget, "days": days})
            return {"ok": True, "data": resultado}
        except urllib.error.HTTPError as exc:
            return {"ok": False, "error": self._http_error(exc), "data": resultado}
        except Exception as exc:
            return {"ok": False, "error": str(exc), "data": resultado}

    def _post(self, path: str, payload: dict, token: str) -> dict:
        payload["access_token"] = token
        data = urllib.parse.urlencode(payload).encode()
        url = f"https://graph.facebook.com/{_VERSION}/{path}"
        req = urllib.request.Request(url, data=data, headers={"User-Agent": _UA}, method="POST")
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode())

    def _fail(self, step: str, data: dict, resultado: dict) -> dict:
        err = data.get("error", {})
        return {"ok": False, "error": f"[{step}] {err.get('message', str(err))}", "data": resultado}

    def _http_error(self, exc: urllib.error.HTTPError) -> str:
        try:
            err = json.loads(exc.read().decode())
            return err.get("error", {}).get("message", str(exc))
        except Exception:
            return str(exc)

    def _end_time(self, days: int) -> str:
        end = datetime.now(timezone.utc) + timedelta(days=days)
        return end.strftime("%Y-%m-%dT%H:%M:%S%z")
