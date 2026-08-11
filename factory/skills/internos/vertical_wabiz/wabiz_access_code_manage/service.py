"""CRUD minimo de wabiz_access_codes: crea/lista/desactiva codigos de registro del bot WhatsApp."""
from __future__ import annotations
from factory.engine import SupabaseClient

_TABLE = "wabiz_access_codes"


class WabizAccessCodeManageService:

    def ejecutar(self, context: dict) -> dict:
        if not isinstance(context, dict):
            return {"ok": False, "error": "context debe ser dict"}

        action = str(context.get("action") or "create").strip().lower()
        if action == "create":
            return self._create(context)
        if action == "list":
            return self._list(context)
        if action == "deactivate":
            return self._deactivate(context)
        return {"ok": False, "error": f"action no soportada: {action} (usa create|list|deactivate)"}

    def _create(self, context: dict) -> dict:
        codigo     = self._str(context, "codigo")
        empresa_id = self._str(context, "empresa_id")
        user_mode  = context.get("user_mode")
        role       = self._str(context, "role") or "user"

        if not codigo:
            return {"ok": False, "error": "codigo requerido"}
        if not empresa_id:
            return {"ok": False, "error": "empresa_id requerido"}
        if not isinstance(user_mode, list) or not user_mode or not all(isinstance(m, str) and m.strip() for m in user_mode):
            return {"ok": False, "error": "user_mode requerido como lista de strings, ej. [\"duralon_pedidos\"]"}

        row = {
            "codigo":     codigo,
            "empresa_id": empresa_id,
            "user_mode":  user_mode,
            "role":       role,
            "activo":     True,
        }

        if context.get("dry_run", True):
            return {"ok": True, "data": {"dry_run": True, "payload": row}}

        db = SupabaseClient(context)
        result = db.rest_upsert(_TABLE, row, on_conflict="codigo")
        if not result.get("ok"):
            return result
        return {"ok": True, "data": {"codigo": codigo, "stored": True, "row": result.get("data")}}

    def _list(self, context: dict) -> dict:
        empresa_id = self._str(context, "empresa_id")
        filters: dict = {}
        if empresa_id:
            filters["empresa_id"] = empresa_id
        if "activo" in context and context.get("activo") is not None:
            filters["activo"] = "true" if context.get("activo") else "false"

        db = SupabaseClient(context)
        result = db.rest_select(_TABLE, filters=filters, order="codigo")
        if not result.get("ok"):
            return result
        return {"ok": True, "data": {"codigos": result.get("data") or []}}

    def _deactivate(self, context: dict) -> dict:
        codigo = self._str(context, "codigo")
        if not codigo:
            return {"ok": False, "error": "codigo requerido"}

        if context.get("dry_run", True):
            return {"ok": True, "data": {"dry_run": True, "codigo": codigo, "would_deactivate": True}}

        db = SupabaseClient(context)
        result = db.rest_update(_TABLE, {"activo": False}, {"codigo": codigo})
        if not result.get("ok"):
            return result
        return {"ok": True, "data": {"codigo": codigo, "deactivated": True}}

    def _str(self, context: dict, key: str):
        val = context.get(key)
        return val.strip() if isinstance(val, str) and val.strip() else None
