from __future__ import annotations

from factory.engine import SupabaseClient

_SCHEMA = "stock4all"


class ErpInventoryWarehouseManageService:
    """CRUD de almacenes, multiempresa (columna company_id), en el schema
    propio del modulo Stock4All (stock4all.warehouses) -- no en el schema
    operativo de ninguna empresa. Igual patron que platform.modulos: el
    schema es infraestructura del modulo, no identidad de cliente.
    """

    def ejecutar(self, context: dict) -> dict:
        action = str(context.get("action") or "list").strip()
        company_id = str(context.get("company_id") or context.get("empresa_id") or "").strip()
        if not company_id:
            return {"ok": False, "error": "company_id requerido"}

        if action == "list":
            return self._list(company_id)
        if action == "create":
            return self._create(context, company_id)
        if action == "ensure_default":
            return self._ensure_default(context, company_id)
        return {"ok": False, "error": f"action invalido: {action}. Usa list|create|ensure_default"}

    def _db(self) -> SupabaseClient:
        return SupabaseClient({"schema": _SCHEMA})

    def _list(self, company_id: str) -> dict:
        result = self._db().rest_select(
            "warehouses",
            filters={"company_id": company_id, "status": "active"},
            select="id,folio,company_id,code,name,is_default,status,created_at",
            order="is_default.desc,code.asc",
            limit=200,
        )
        if not result.get("ok"):
            return result
        return {"ok": True, "data": {"warehouses": result.get("data") or []}}

    def _create(self, context: dict, company_id: str) -> dict:
        code = str(context.get("code") or "").strip().upper()
        name = str(context.get("name") or "").strip()
        is_default = bool(context.get("is_default", False))
        if not code or not name:
            return {"ok": False, "error": "code y name requeridos"}

        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run: no se creo almacen", "data": {"code": code, "name": name, "company_id": company_id}}

        db = self._db()
        if is_default:
            db.rest_update("warehouses", {"is_default": False}, {"company_id": company_id, "is_default": "true"})

        result = db.rest_insert("warehouses", {
            "company_id": company_id,
            "code": code,
            "name": name,
            "is_default": is_default,
            "status": "active",
        })
        if not result.get("ok"):
            return result
        data = result.get("data") or []
        return {"ok": True, "data": {"warehouse": data[0] if data else None}}

    def _ensure_default(self, context: dict, company_id: str) -> dict:
        db = self._db()
        existing = db.rest_select(
            "warehouses",
            filters={"company_id": company_id, "status": "active"},
            select="id,folio,company_id,code,name,is_default,status",
            order="is_default.desc,created_at.asc",
            limit=1,
        )
        if not existing.get("ok"):
            return existing
        rows = existing.get("data") or []
        if rows:
            return {"ok": True, "data": {"warehouse": rows[0], "created": False}}

        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run: crearia almacen PRINCIPAL", "data": {"created": True}}

        result = db.rest_insert("warehouses", {
            "company_id": company_id,
            "code": "PRINCIPAL",
            "name": "Almacen principal",
            "is_default": True,
            "status": "active",
        })
        if not result.get("ok"):
            return result
        data = result.get("data") or []
        return {"ok": True, "data": {"warehouse": data[0] if data else None, "created": True}}
