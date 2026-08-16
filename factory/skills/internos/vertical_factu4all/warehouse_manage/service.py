from __future__ import annotations

from factory.engine import SupabaseClient

_SCHEMA = "factu4all"
_DEFAULT_CODE = "PRINCIPAL"


class WarehouseManageService:
    def ejecutar(self, context: dict) -> dict:
        company_id = str(context.get("company_id") or context.get("empresa_id") or "").strip()
        if not company_id:
            return {"ok": False, "error": "company_id_requerido"}

        action = str(context.get("action") or "list").strip().lower()
        db = SupabaseClient({**context, "schema": _SCHEMA})

        if action == "list":
            return self._list(db, company_id)
        if action == "ensure_default":
            return self._ensure_default(db, company_id)

        code = str(context.get("code") or "").strip().upper()
        name = str(context.get("name") or "").strip()
        if not code or not name:
            return {"ok": False, "error": "code_y_name_requeridos"}
        is_default = bool(context.get("is_default", False))

        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run: no se escribio en warehouses", "data": {"company_id": company_id, "code": code, "name": name}}

        existing = db.rest_select("warehouses", filters={"company_id": f"eq.{company_id}", "code": f"eq.{code}"}, select="id", limit=1)
        if not existing.get("ok"):
            return {"ok": False, "error": "db_query_failed", "data": {"detail": existing.get("error")}}

        if is_default:
            db.rest_update("warehouses", {"is_default": False}, {"company_id": f"eq.{company_id}"})

        if existing.get("data"):
            res = db.rest_update("warehouses", {"name": name, "is_default": is_default, "status": context.get("status") or "active"}, {"company_id": f"eq.{company_id}", "code": f"eq.{code}"})
        else:
            row = {"folio": f"WH-{company_id}-{code}", "company_id": company_id, "code": code, "name": name, "is_default": is_default, "status": "active"}
            res = db.rest_insert("warehouses", row)

        if not res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": res.get("error")}}
        return {"ok": True, "data": {"warehouse": (res.get("data") or [{}])[0]}}

    def _list(self, db: SupabaseClient, company_id: str) -> dict:
        res = db.rest_select("warehouses", filters={"company_id": f"eq.{company_id}"}, select="*", order="is_default.desc,code.asc")
        if not res.get("ok"):
            return {"ok": False, "error": "db_query_failed", "data": {"detail": res.get("error")}}
        return {"ok": True, "data": {"warehouses": res.get("data") or []}}

    def _ensure_default(self, db: SupabaseClient, company_id: str) -> dict:
        existing = db.rest_select("warehouses", filters={"company_id": f"eq.{company_id}", "is_default": "eq.true"}, select="*", limit=1)
        if existing.get("ok") and existing.get("data"):
            return {"ok": True, "data": {"warehouse": existing["data"][0]}}

        any_wh = db.rest_select("warehouses", filters={"company_id": f"eq.{company_id}"}, select="*", limit=1)
        if any_wh.get("ok") and any_wh.get("data"):
            return {"ok": True, "data": {"warehouse": any_wh["data"][0]}}

        row = {"folio": f"WH-{company_id}-{_DEFAULT_CODE}", "company_id": company_id, "code": _DEFAULT_CODE, "name": "Almacén principal", "is_default": True, "status": "active"}
        ins = db.rest_insert("warehouses", row)
        if not ins.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": ins.get("error")}}
        return {"ok": True, "data": {"warehouse": (ins.get("data") or [row])[0]}}
