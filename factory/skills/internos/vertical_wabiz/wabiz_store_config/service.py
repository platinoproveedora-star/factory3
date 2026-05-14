"""Guarda o actualiza credenciales WhatsApp Business por empresa_id en wabiz_config."""
from __future__ import annotations
import datetime as dt
import json
import os
import urllib.request


class WabizStoreConfigService:

    def ejecutar(self, context: dict) -> dict:
        empresa_id          = self._str(context, "empresa_id")
        phone_number_id     = self._str(context, "phone_number_id")
        access_token        = self._str(context, "access_token")
        verify_token        = self._str(context, "verify_token")

        if not empresa_id:
            return {"ok": False, "error": "empresa_id requerido"}
        if not phone_number_id:
            return {"ok": False, "error": "phone_number_id requerido"}
        if not access_token:
            return {"ok": False, "error": "access_token requerido"}
        if not verify_token:
            return {"ok": False, "error": "verify_token requerido"}

        business_account_id = self._str(context, "business_account_id") or ""
        graph_version       = self._str(context, "graph_version") or "v24.0"

        row = {
            "empresa_id":          empresa_id,
            "phone_number_id":     phone_number_id,
            "business_account_id": business_account_id,
            "access_token":        access_token,
            "verify_token":        verify_token,
            "graph_version":       graph_version,
            "updated_at":          dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        }

        if context.get("dry_run", True):
            return {"ok": True, "data": {"dry_run": True, "payload": row}}

        try:
            result = self._upsert(row)
            return {"ok": True, "data": {"empresa_id": empresa_id, "stored": True}}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _upsert(self, row: dict) -> list:
        url  = f"{os.getenv('SUPABASE_URL')}/rest/v1/wabiz_config"
        data = json.dumps(row).encode()
        req  = urllib.request.Request(
            url, data=data, method="POST",
            headers={
                "apikey":        os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
                "Authorization": f"Bearer {os.getenv('SUPABASE_SERVICE_ROLE_KEY', '')}",
                "Content-Type":  "application/json",
                "Prefer":        "resolution=merge-duplicates,return=representation",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())

    def _str(self, context: dict, key: str):
        val = context.get(key)
        return val.strip() if isinstance(val, str) and val.strip() else None
