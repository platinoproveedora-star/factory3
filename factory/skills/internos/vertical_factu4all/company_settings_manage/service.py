from __future__ import annotations

from factory.engine import SupabaseClient

_SCHEMA = "factu4all"
_FIELDS = ["country", "default_pac_provider", "default_environment"]


class CompanySettingsManageService:
    def ejecutar(self, context: dict) -> dict:
        company_id = str(context.get("company_id") or context.get("empresa_id") or "").strip()
        if not company_id:
            return {"ok": False, "error": "company_id_requerido"}

        action = str(context.get("action") or "get").strip().lower()
        db = SupabaseClient({**context, "schema": _SCHEMA})

        if action == "get":
            res = db.rest_select("factu4all_company_settings", filters={"company_id": f"eq.{company_id}"}, select="*", limit=1)
            if not res.get("ok"):
                return {"ok": False, "error": "db_query_failed", "data": {"detail": res.get("error")}}
            rows = res.get("data") or []
            return {"ok": True, "data": {"settings": rows[0] if rows else None}}

        values = {key: context[key] for key in _FIELDS if key in context}
        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run: no se escribio en factu4all_company_settings", "data": {"company_id": company_id, **values}}

        existing = db.rest_select("factu4all_company_settings", filters={"company_id": f"eq.{company_id}"}, select="id", limit=1)
        if not existing.get("ok"):
            return {"ok": False, "error": "db_query_failed", "data": {"detail": existing.get("error")}}

        if existing.get("data"):
            res = db.rest_update("factu4all_company_settings", values, {"company_id": f"eq.{company_id}"})
        else:
            row = {
                "folio": f"CFG-{company_id}",
                "company_id": company_id,
                "country": values.get("country") or "MX",
                "default_pac_provider": values.get("default_pac_provider") or "facturama",
                "default_environment": values.get("default_environment") or "sandbox",
            }
            res = db.rest_insert("factu4all_company_settings", row)

        if not res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": res.get("error")}}
        return {"ok": True, "data": {"settings": (res.get("data") or [{}])[0]}}
