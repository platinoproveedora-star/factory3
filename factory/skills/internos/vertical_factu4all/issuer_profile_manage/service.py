from __future__ import annotations

from factory.engine import SupabaseClient

_SCHEMA = "factu4all"
_FIELDS = [
    "legal_name", "fiscal_regime", "expedition_place", "commercial_name",
    "fiscal_email", "fiscal_address", "pac_provider", "pac_account_id",
    "csd_status", "environment", "status",
]


class IssuerProfileManageService:
    def ejecutar(self, context: dict) -> dict:
        company_id = str(context.get("company_id") or context.get("empresa_id") or "").strip()
        if not company_id:
            return {"ok": False, "error": "company_id_requerido"}

        action = str(context.get("action") or "list").strip().lower()
        db = SupabaseClient({**context, "schema": _SCHEMA})

        if action == "list":
            return self._list(db, company_id)

        rfc = str(context.get("rfc") or "").strip().upper()
        if not rfc:
            return {"ok": False, "error": "rfc_requerido"}

        values = {key: context[key] for key in _FIELDS if key in context}
        if "legal_name" in context or action == "create":
            values.setdefault("legal_name", str(context.get("legal_name") or "").strip())

        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run: no se escribio en issuer_profiles", "data": {"company_id": company_id, "rfc": rfc, **values}}

        existing = db.rest_select("issuer_profiles", filters={"company_id": f"eq.{company_id}", "rfc": f"eq.{rfc}"}, select="id", limit=1)
        if not existing.get("ok"):
            return {"ok": False, "error": "db_query_failed", "data": {"detail": existing.get("error")}}

        if existing.get("data"):
            res = db.rest_update("issuer_profiles", values, {"company_id": f"eq.{company_id}", "rfc": f"eq.{rfc}"})
        else:
            row = {
                "folio": f"ISS-{company_id}-{rfc}",
                "company_id": company_id,
                "rfc": rfc,
                "legal_name": values.get("legal_name") or rfc,
                "status": values.get("status") or "draft",
                "environment": values.get("environment") or "sandbox",
                "csd_status": values.get("csd_status") or "pending",
                **{key: value for key, value in values.items() if key not in {"legal_name", "status", "environment", "csd_status"}},
            }
            res = db.rest_insert("issuer_profiles", row)

        if not res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": res.get("error")}}
        return {"ok": True, "data": {"issuer_profile": (res.get("data") or [{}])[0]}}

    def _list(self, db: SupabaseClient, company_id: str) -> dict:
        res = db.rest_select("issuer_profiles", filters={"company_id": f"eq.{company_id}"}, select="*", order="created_at.desc")
        if not res.get("ok"):
            return {"ok": False, "error": "db_query_failed", "data": {"detail": res.get("error")}}
        return {"ok": True, "data": {"issuer_profiles": res.get("data") or []}}
