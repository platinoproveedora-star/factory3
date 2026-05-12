"""Lista todas las cuentas publicitarias accesibles con el token Meta."""
from __future__ import annotations
import json, os, urllib.request, urllib.parse

_VERSION = "v24.0"
_UA = "FactoryFactory/0.1 (+https://github.com/)"
_STATUS_MAP = {1: "ACTIVO", 2: "DESHABILITADO", 3: "PENDIENTE_PAGO", 101: "CERRADO"}


class MetaAdsListAdAccountsService:

    def ejecutar(self, context: dict) -> dict:
        token = context.get("access_token") or os.getenv("META_ACCESS_TOKEN", "")
        if not token:
            return {"ok": False, "error": "access_token requerido"}

        limit = int(context.get("limit", 25))

        try:
            fields = "id,name,account_status,currency,timezone_name,amount_spent,business"
            data = self._get("me/adaccounts", {"fields": fields, "limit": limit}, token)

            if "error" in data:
                err = data["error"]
                return {"ok": False, "error": err.get("message", str(err))}

            cuentas = []
            for ac in data.get("data", []):
                status = ac.get("account_status", 0)
                cuentas.append({
                    "ad_account_id": ac.get("id"),
                    "nombre":        ac.get("name"),
                    "estado":        _STATUS_MAP.get(status, f"DESCONOCIDO({status})"),
                    "moneda":        ac.get("currency"),
                    "zona_horaria":  ac.get("timezone_name"),
                    "gastado_total": ac.get("amount_spent"),
                    "negocio":       (ac.get("business") or {}).get("name"),
                })

            return {"ok": True, "data": {"total": len(cuentas), "cuentas": cuentas}}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _get(self, path: str, params: dict, token: str) -> dict:
        params["access_token"] = token
        qs = urllib.parse.urlencode(params)
        url = f"https://graph.facebook.com/{_VERSION}/{path}?{qs}"
        req = urllib.request.Request(url, headers={"User-Agent": _UA})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
