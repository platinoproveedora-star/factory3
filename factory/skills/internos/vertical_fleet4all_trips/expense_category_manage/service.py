from __future__ import annotations

from factory.engine import SupabaseClient

_SCHEMA = "fleet4all"


class ExpenseCategoryManageService:
    def ejecutar(self, context: dict) -> dict:
        empresa_id = str(context.get("empresa_id") or context.get("company_id") or "").strip()
        if not empresa_id:
            return {"ok": False, "error": "empresa_id_requerido"}

        action = str(context.get("action") or "list").strip().lower()
        db = SupabaseClient({**context, "schema": context.get("schema") or _SCHEMA})

        if action == "list":
            return self._list(db, empresa_id, context)
        if action == "create":
            return self._create(db, empresa_id, context)
        if action == "toggle":
            return self._toggle(db, empresa_id, context)
        return {"ok": False, "error": "action_invalida"}

    def _list(self, db: SupabaseClient, empresa_id: str, context: dict) -> dict:
        filters = {"empresa_id": f"eq.{empresa_id}"}
        if context.get("solo_activas"):
            filters["activo"] = "eq.true"
        res = db.rest_select("expense_categories", filters=filters, select="id,nombre,activo", order="nombre.asc")
        if not res.get("ok"):
            return {"ok": False, "error": "db_query_failed", "data": {"detail": res.get("error")}}
        return {"ok": True, "data": {"categorias": res.get("data") or []}}

    def _create(self, db: SupabaseClient, empresa_id: str, context: dict) -> dict:
        nombre = str(context.get("nombre") or "").strip()
        if not nombre:
            return {"ok": False, "error": "nombre_requerido"}

        existing_res = db.rest_select("expense_categories", filters={"empresa_id": f"eq.{empresa_id}"}, select="id,nombre,activo")
        if not existing_res.get("ok"):
            return {"ok": False, "error": "db_query_failed", "data": {"detail": existing_res.get("error")}}
        match = next((c for c in (existing_res.get("data") or []) if str(c.get("nombre", "")).lower() == nombre.lower()), None)

        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run: no se escribio en fleet4all.expense_categories", "data": {"categoria": {"nombre": nombre, "activo": True}}}

        if match:
            if match.get("activo"):
                return {"ok": False, "error": "categoria_ya_existe"}
            res = db.rest_update("expense_categories", {"activo": True}, {"empresa_id": f"eq.{empresa_id}", "id": f"eq.{match['id']}"})
            if not res.get("ok"):
                return {"ok": False, "error": "db_persistence_failed", "data": {"detail": res.get("error")}}
            return {"ok": True, "data": {"categoria": (res.get("data") or [{}])[0]}}

        res = db.rest_insert("expense_categories", {"empresa_id": empresa_id, "nombre": nombre, "activo": True})
        if not res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": res.get("error")}}
        return {"ok": True, "data": {"categoria": (res.get("data") or [{}])[0]}}

    def _toggle(self, db: SupabaseClient, empresa_id: str, context: dict) -> dict:
        cat_id = str(context.get("id") or "").strip()
        if not cat_id:
            return {"ok": False, "error": "id_requerido"}
        activo = bool(context.get("activo"))

        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run: no se actualizo", "data": {"categoria": {"id": cat_id, "activo": activo}}}

        res = db.rest_update("expense_categories", {"activo": activo}, {"empresa_id": f"eq.{empresa_id}", "id": f"eq.{cat_id}"})
        if not res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": res.get("error")}}
        rows = res.get("data") or []
        if not rows:
            return {"ok": False, "error": "categoria_no_encontrada"}
        return {"ok": True, "data": {"categoria": rows[0]}}
