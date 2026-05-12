"""Actualiza presupuesto, estado, bid o fechas de un conjunto de anuncios existente."""
from __future__ import annotations
import json, os, urllib.request, urllib.parse

_VERSION = "v24.0"
_UA = "FactoryFactory/0.1 (+https://github.com/)"


class MetaAdsUpdateAdsetService:

    def ejecutar(self, context: dict) -> dict:
        token = context.get("access_token") or os.getenv("META_ACCESS_TOKEN", "")
        adset_id = (context.get("adset_id") or "").strip()

        if not token:
            return {"ok": False, "error": "access_token requerido"}
        if not adset_id:
            return {"ok": False, "error": "adset_id requerido"}

        cambios: dict = {}
        if context.get("nombre") or context.get("name"):
            cambios["name"] = (context.get("nombre") or context.get("name")).strip()
        if context.get("estado") or context.get("status"):
            cambios["status"] = (context.get("estado") or context.get("status")).upper()
        if context.get("daily_budget"):
            cambios["daily_budget"] = str(int(float(context["daily_budget"]) * 100))
        if context.get("lifetime_budget"):
            cambios["lifetime_budget"] = str(int(float(context["lifetime_budget"]) * 100))
        if context.get("bid_amount"):
            cambios["bid_amount"] = str(int(float(context["bid_amount"]) * 100))
        if context.get("start_time"):
            cambios["start_time"] = context["start_time"]
        if context.get("end_time"):
            cambios["end_time"] = context["end_time"]
        if context.get("targeting"):
            cambios["targeting"] = json.dumps(context["targeting"])

        if not cambios:
            return {"ok": False, "error": "Sin cambios. Enviar al menos uno de: nombre, estado, daily_budget, bid_amount, start_time, end_time, targeting"}

        if context.get("dry_run", True):
            return {"ok": True, "data": {"dry_run": True, "adset_id": adset_id, "cambios": cambios}}

        try:
            data = self._post(adset_id, cambios, token)
            if "error" in data:
                err = data["error"]
                return {"ok": False, "error": err.get("message", str(err))}
            return {"ok": True, "data": {"adset_id": adset_id, "actualizado": True, "cambios": cambios}}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _post(self, path: str, payload: dict, token: str) -> dict:
        payload["access_token"] = token
        data = urllib.parse.urlencode(payload).encode()
        url = f"https://graph.facebook.com/{_VERSION}/{path}"
        req = urllib.request.Request(url, data=data, headers={"User-Agent": _UA}, method="POST")
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
