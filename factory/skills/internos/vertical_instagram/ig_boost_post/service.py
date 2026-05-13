from __future__ import annotations
import json, os, urllib.request, urllib.parse, urllib.error

_VERSION = "v24.0"
_UA = "FactoryFactory/0.1 (+https://github.com/)"

_OBJECTIVES = {
    "OUTCOME_AWARENESS", "OUTCOME_TRAFFIC", "OUTCOME_ENGAGEMENT",
    "OUTCOME_LEADS", "OUTCOME_SALES",
}


class IgBoostPostService:

    def ejecutar(self, context: dict) -> dict:
        post_id = (context.get("post_id") or "").strip()
        access_token = (context.get("access_token") or os.getenv("IG_ACCESS_TOKEN") or os.getenv("META_ACCESS_TOKEN") or "").strip()
        ad_account_id = (context.get("ad_account_id") or os.getenv("META_AD_ACCOUNT_ID") or "").strip()
        page_id = (context.get("page_id") or os.getenv("IG_PAGE_ID") or os.getenv("META_PAGE_ID") or "").strip()
        ig_actor_id = (context.get("ig_actor_id") or os.getenv("IG_USER_ID") or os.getenv("IG_ACTOR_ID") or "").strip()
        link_destino = (context.get("link") or f"https://www.instagram.com/{context.get('username') or 'platinoproveedora'}/").strip()
        budget_pesos = float(context.get("budget_pesos") or context.get("presupuesto") or 0)
        dias = int(context.get("dias") or 7)
        objetivo = (context.get("objetivo") or "OUTCOME_ENGAGEMENT").upper()
        nombre = (context.get("nombre") or f"Boost_{post_id[:12]}").strip()

        if not post_id:
            return {"ok": False, "error": "post_id requerido"}
        if not access_token:
            return {"ok": False, "error": "access_token requerido (o IG_ACCESS_TOKEN en env)"}
        if not ad_account_id:
            return {"ok": False, "error": "ad_account_id requerido (o META_AD_ACCOUNT_ID en env)"}
        if not page_id:
            return {"ok": False, "error": "page_id requerido (o IG_PAGE_ID en env)"}
        if budget_pesos <= 0:
            return {"ok": False, "error": "budget_pesos debe ser mayor a 0"}
        if objetivo not in _OBJECTIVES:
            return {"ok": False, "error": f"objetivo inválido. Opciones: {sorted(_OBJECTIVES)}"}

        if not ad_account_id.startswith("act_"):
            ad_account_id = f"act_{ad_account_id}"

        budget_centavos = str(int(budget_pesos * 100))
        targeting = context.get("targeting") or {"geo_locations": {"countries": ["MX"]}, "age_min": 18, "age_max": 65}

        if context.get("dry_run", True):
            return {"ok": True, "data": {
                "dry_run":        True,
                "post_id":        post_id,
                "ad_account_id":  ad_account_id,
                "objetivo":       objetivo,
                "budget_pesos":   budget_pesos,
                "dias":           dias,
            }}

        pasos = []
        try:
            # 1. Campaña
            c = self._post(f"{ad_account_id}/campaigns", {
                "name":                            f"[Boost] {nombre}",
                "objective":                       objetivo,
                "status":                          "ACTIVE",
                "special_ad_categories":           json.dumps([]),
                "is_adset_budget_sharing_enabled": "false",
            }, access_token)
            if "error" in c:
                return {"ok": False, "error": f"campaign: {c['error'].get('message', c['error'])}"}
            campaign_id = c["id"]
            pasos.append({"paso": "campaign", "id": campaign_id})

            # 2. Ad set
            a = self._post(f"{ad_account_id}/adsets", {
                "name":              f"[Boost] {nombre}",
                "campaign_id":       campaign_id,
                "optimization_goal": "REACH",
                "billing_event":     "IMPRESSIONS",
                "bid_strategy":      "LOWEST_COST_WITHOUT_CAP",
                "lifetime_budget":   budget_centavos,
                "end_time":          self._end_time(dias),
                "targeting":         json.dumps(targeting),
                "status":            "ACTIVE",
            }, access_token)
            if "error" in a:
                return {"ok": False, "error": f"adset: {a['error'].get('message', a['error'])}", "pasos": pasos}
            adset_id = a["id"]
            pasos.append({"paso": "adset", "id": adset_id})

            # 3. Creative usando el post existente de IG
            story_spec: dict = {
                "page_id": page_id,
                "instagram_image_data": {
                    "instagram_media_id": post_id,
                    "link": link_destino,
                },
            }

            cr = self._post(f"{ad_account_id}/adcreatives", {
                "name":              f"[Boost] {nombre}",
                "object_story_spec": json.dumps(story_spec),
            }, access_token)
            if "error" in cr:
                return {"ok": False, "error": f"creative: {cr['error'].get('message', cr['error'])}", "pasos": pasos}
            creative_id = cr["id"]
            pasos.append({"paso": "creative", "id": creative_id})

            # 4. Ad
            ad = self._post(f"{ad_account_id}/ads", {
                "name":       f"[Boost] {nombre}",
                "adset_id":   adset_id,
                "creative":   json.dumps({"creative_id": creative_id}),
                "status":     "ACTIVE",
            }, access_token)
            if "error" in ad:
                return {"ok": False, "error": f"ad: {ad['error'].get('message', ad['error'])}", "pasos": pasos}
            ad_id = ad["id"]
            pasos.append({"paso": "ad", "id": ad_id})

            return {"ok": True, "data": {
                "campaign_id": campaign_id,
                "adset_id":    adset_id,
                "creative_id": creative_id,
                "ad_id":       ad_id,
                "post_id":     post_id,
                "objetivo":    objetivo,
                "dias":        dias,
                "budget_pesos": budget_pesos,
                "pasos":       pasos,
            }}

        except urllib.error.HTTPError as exc:
            try:
                err = json.loads(exc.read().decode())
                msg = err.get("error", {}).get("message", str(exc))
            except Exception:
                msg = str(exc)
            return {"ok": False, "error": msg, "pasos": pasos}
        except Exception as exc:
            return {"ok": False, "error": str(exc), "pasos": pasos}

    def _post(self, path: str, payload: dict, token: str) -> dict:
        payload["access_token"] = token
        data = urllib.parse.urlencode(payload).encode()
        url = f"https://graph.facebook.com/{_VERSION}/{path}"
        req = urllib.request.Request(url, data=data, headers={"User-Agent": _UA}, method="POST")
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())

    def _end_time(self, dias: int) -> str:
        import datetime
        end = datetime.datetime.utcnow() + datetime.timedelta(days=dias)
        return end.strftime("%Y-%m-%dT%H:%M:%S+0000")
