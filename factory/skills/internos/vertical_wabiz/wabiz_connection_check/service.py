"""Valida token y phone_number_id WhatsApp Business contra Graph API."""
from __future__ import annotations
import json
import os
import urllib.parse
import urllib.request

_UA = "FactoryFactory/0.1 (+https://github.com/)"


class WabizConnectionCheckService:

    def ejecutar(self, context: dict) -> dict:
        empresa_id      = context.get("empresa_id")
        token           = context.get("access_token")
        phone_number_id = context.get("phone_number_id")
        graph_version   = context.get("graph_version", "v24.0")

        if empresa_id and not (token and phone_number_id):
            cfg = self._load_config(empresa_id)
            if not cfg:
                return {"ok": False, "error": f"No hay config para empresa_id={empresa_id}"}
            token           = token or cfg.get("access_token")
            phone_number_id = phone_number_id or cfg.get("phone_number_id")
            graph_version   = cfg.get("graph_version", graph_version)

        if not token:
            return {"ok": False, "error": "access_token requerido"}
        if not phone_number_id:
            return {"ok": False, "error": "phone_number_id requerido"}

        try:
            fields = "display_phone_number,verified_name,quality_rating,account_mode,platform_type"
            data   = self._graph_get(phone_number_id, {"fields": fields}, token, graph_version)

            if "error" in data:
                err = data["error"]
                return {"ok": False, "error": err.get("message", str(err))}

            return {"ok": True, "data": {
                "conectado":        True,
                "phone_number_id":  data.get("id"),
                "display_phone":    data.get("display_phone_number"),
                "verified_name":    data.get("verified_name"),
                "quality_rating":   data.get("quality_rating"),
                "account_mode":     data.get("account_mode"),
                "platform_type":    data.get("platform_type"),
            }}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _load_config(self, empresa_id: str) -> dict | None:
        try:
            qs  = urllib.parse.urlencode({"empresa_id": f"eq.{empresa_id}", "select": "access_token,phone_number_id,graph_version", "limit": "1"})
            url = f"{os.getenv('SUPABASE_URL')}/rest/v1/wabiz_config?{qs}"
            req = urllib.request.Request(url, headers={
                "apikey":        os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
                "Authorization": f"Bearer {os.getenv('SUPABASE_SERVICE_ROLE_KEY', '')}",
                "Accept":        "application/json",
            })
            with urllib.request.urlopen(req, timeout=10) as r:
                rows = json.loads(r.read().decode())
                return rows[0] if rows else None
        except Exception:
            return None

    def _graph_get(self, path: str, params: dict, token: str, version: str) -> dict:
        params["access_token"] = token
        qs  = urllib.parse.urlencode(params)
        url = f"https://graph.facebook.com/{version}/{path}?{qs}"
        req = urllib.request.Request(url, headers={"User-Agent": _UA})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
