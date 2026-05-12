"""Actualiza nombre, estado o presupuesto de una campaña Meta Ads existente."""
from __future__ import annotations
import json, os, urllib.request, urllib.parse

_VERSION = "v24.0"
_UA = "FactoryFactory/0.1 (+https://github.com/)"
_ESTADOS = {"ACTIVE", "PAUSED", "DELETED", "ARCHIVED"}


class MetaAdsUpdateCampaignService:

    def ejecutar(self, context: dict) -> dict:
        token = context.get("access_token") or os.getenv("META_ACCESS_TOKEN", "")
        campaign_id = (context.get("campaign_id") or "").strip()

        if not token:
            return {"ok": False, "error": "access_token requerido"}
        if not campaign_id:
            return {"ok": False, "error": "campaign_id requerido"}

        cambios: dict = {}
        if context.get("nombre") or context.get("name"):
            cambios["name"] = (context.get("nombre") or context.get("name")).strip()
        if context.get("estado") or context.get("status"):
            estado = (context.get("estado") or context.get("status")).upper()
            if estado not in _ESTADOS:
                return {"ok": False, "error": f"estado inválido. Valores: {sorted(_ESTADOS)}"}
            cambios["status"] = estado
        if context.get("daily_budget"):
            cambios["daily_budget"] = str(int(float(context["daily_budget"]) * 100))
        if context.get("lifetime_budget"):
            cambios["lifetime_budget"] = str(int(float(context["lifetime_budget"]) * 100))

        if not cambios:
            return {"ok": False, "error": "Sin cambios. Enviar al menos: nombre, estado, daily_budget o lifetime_budget"}

        if context.get("dry_run", True):
            return {"ok": True, "data": {"dry_run": True, "campaign_id": campaign_id, "cambios": cambios}}

        try:
            data = self._post(campaign_id, cambios, token)
            if "error" in data:
                err = data["error"]
                return {"ok": False, "error": err.get("message", str(err))}
            return {"ok": True, "data": {"campaign_id": campaign_id, "actualizado": True, "cambios": cambios}}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _post(self, path: str, payload: dict, token: str) -> dict:
        payload["access_token"] = token
        data = urllib.parse.urlencode(payload).encode()
        url = f"https://graph.facebook.com/{_VERSION}/{path}"
        req = urllib.request.Request(url, data=data, headers={"User-Agent": _UA}, method="POST")
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
