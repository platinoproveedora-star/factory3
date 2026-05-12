"""Valida token y acceso a cuenta publicitaria Meta Ads."""
from __future__ import annotations
import json, os, urllib.request, urllib.parse

_VERSION = "v24.0"
_UA = "FactoryFactory/0.1 (+https://github.com/)"
_STATUS_MAP = {1: "ACTIVO", 2: "DESHABILITADO", 3: "PENDIENTE_PAGO", 7: "REVISION_RIESGO",
               9: "EN_GRACIA", 100: "CIERRE_PENDIENTE", 101: "CERRADO"}


class MetaAdsConnectionCheckService:

    def ejecutar(self, context: dict) -> dict:
        token = context.get("access_token") or os.getenv("META_ACCESS_TOKEN", "")
        ad_account_id = context.get("ad_account_id") or os.getenv("META_AD_ACCOUNT_ID", "")

        if not token:
            return {"ok": False, "error": "access_token requerido"}
        if not ad_account_id:
            return {"ok": False, "error": "ad_account_id requerido (ej. act_123456 o 123456)"}

        if not ad_account_id.startswith("act_"):
            ad_account_id = f"act_{ad_account_id}"

        try:
            fields = "id,name,account_status,currency,timezone_name,amount_spent,balance,disable_reason"
            data = self._get(ad_account_id, {"fields": fields}, token)

            if "error" in data:
                err = data["error"]
                return {"ok": False, "error": err.get("message", str(err))}

            account_status = data.get("account_status", 0)
            activo = account_status == 1

            return {"ok": True, "data": {
                "conectado":    activo,
                "ad_account_id": data.get("id"),
                "nombre":       data.get("name"),
                "estado":       _STATUS_MAP.get(account_status, f"DESCONOCIDO({account_status})"),
                "moneda":       data.get("currency"),
                "zona_horaria": data.get("timezone_name"),
                "gastado_total": data.get("amount_spent"),
                "balance":      data.get("balance"),
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
