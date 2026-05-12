"""Orquestador: crea campaña → conjunto → creativo → anuncio en secuencia."""
from __future__ import annotations
import json, os, urllib.request, urllib.parse

_VERSION = "v24.0"
_UA = "FactoryFactory/0.1 (+https://github.com/)"


class MetaAdsPublishFlowService:

    def ejecutar(self, context: dict) -> dict:
        token = context.get("access_token") or os.getenv("META_ACCESS_TOKEN", "")
        ad_account_id = context.get("ad_account_id") or os.getenv("META_AD_ACCOUNT_ID", "")
        page_id = context.get("page_id") or os.getenv("META_PAGE_ID", "")

        nombre_campana = (context.get("nombre_campana") or "").strip()
        objetivo = (context.get("objetivo") or "OUTCOME_TRAFFIC").upper()
        nombre_conjunto = (context.get("nombre_conjunto") or f"{nombre_campana} - Conjunto").strip()
        daily_budget = context.get("daily_budget")
        targeting = context.get("targeting") or {"geo_locations": {"countries": ["MX"]}}
        optimization_goal = (context.get("optimization_goal") or "LINK_CLICKS").upper()
        billing_event = (context.get("billing_event") or "LINK_CLICKS").upper()

        nombre_creativo = (context.get("nombre_creativo") or f"{nombre_campana} - Creativo").strip()
        mensaje = (context.get("mensaje") or "").strip()
        link = (context.get("link") or "").strip()
        cta_type = (context.get("cta_type") or "LEARN_MORE").upper()

        nombre_anuncio = (context.get("nombre_anuncio") or f"{nombre_campana} - Anuncio").strip()

        if not token:
            return {"ok": False, "error": "access_token requerido"}
        if not ad_account_id:
            return {"ok": False, "error": "ad_account_id requerido"}
        if not page_id:
            return {"ok": False, "error": "page_id requerido"}
        if not nombre_campana:
            return {"ok": False, "error": "nombre_campana requerido"}
        if not link:
            return {"ok": False, "error": "link requerido (URL destino)"}
        if not daily_budget:
            return {"ok": False, "error": "daily_budget requerido (en pesos)"}

        if not ad_account_id.startswith("act_"):
            ad_account_id = f"act_{ad_account_id}"

        if context.get("dry_run", True):
            return {"ok": True, "data": {
                "dry_run":         True,
                "nombre_campana":  nombre_campana,
                "objetivo":        objetivo,
                "daily_budget":    daily_budget,
                "link":            link,
                "pasos":           ["create_campaign", "create_adset", "create_creative", "create_ad"],
            }}

        resultado: dict = {"pasos": []}
        try:
            # 1. Campaign
            camp = self._post(f"{ad_account_id}/campaigns", {
                "name": nombre_campana,
                "objective": objetivo,
                "status": "PAUSED",
                "special_ad_categories": json.dumps([]),
            }, token)
            if "error" in camp:
                return {"ok": False, "error": f"[campaign] {camp['error'].get('message', str(camp['error']))}", "data": resultado}
            campaign_id = camp["id"]
            resultado["campaign_id"] = campaign_id
            resultado["pasos"].append("campaign_creada")

            # 2. Ad Set
            adset = self._post(f"{ad_account_id}/adsets", {
                "name": nombre_conjunto,
                "campaign_id": campaign_id,
                "billing_event": billing_event,
                "optimization_goal": optimization_goal,
                "daily_budget": str(int(float(daily_budget) * 100)),
                "targeting": json.dumps(targeting),
                "status": "PAUSED",
            }, token)
            if "error" in adset:
                return {"ok": False, "error": f"[adset] {adset['error'].get('message', str(adset['error']))}", "data": resultado}
            adset_id = adset["id"]
            resultado["adset_id"] = adset_id
            resultado["pasos"].append("adset_creado")

            # 3. Creative
            link_data: dict = {"link": link, "call_to_action": {"type": cta_type, "value": {"link": link}}}
            if mensaje:
                link_data["message"] = mensaje
            if context.get("image_url"):
                link_data["picture"] = context["image_url"]

            creative = self._post(f"{ad_account_id}/adcreatives", {
                "name": nombre_creativo,
                "object_story_spec": json.dumps({"page_id": page_id, "link_data": link_data}),
            }, token)
            if "error" in creative:
                return {"ok": False, "error": f"[creative] {creative['error'].get('message', str(creative['error']))}", "data": resultado}
            creative_id = creative["id"]
            resultado["creative_id"] = creative_id
            resultado["pasos"].append("creativo_creado")

            # 4. Ad
            ad = self._post(f"{ad_account_id}/ads", {
                "name": nombre_anuncio,
                "adset_id": adset_id,
                "creative": json.dumps({"creative_id": creative_id}),
                "status": "PAUSED",
            }, token)
            if "error" in ad:
                return {"ok": False, "error": f"[ad] {ad['error'].get('message', str(ad['error']))}", "data": resultado}
            resultado["ad_id"] = ad["id"]
            resultado["pasos"].append("anuncio_creado")

            resultado["ok"] = True
            resultado["estado"] = "PAUSED"
            resultado["mensaje"] = "Flujo completado. Activa la campaña cuando estés listo."
            return {"ok": True, "data": resultado}

        except Exception as e:
            return {"ok": False, "error": str(e), "data": resultado}

    def _post(self, path: str, payload: dict, token: str) -> dict:
        payload["access_token"] = token
        data = urllib.parse.urlencode(payload).encode()
        url = f"https://graph.facebook.com/{_VERSION}/{path}"
        req = urllib.request.Request(url, data=data, headers={"User-Agent": _UA}, method="POST")
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
