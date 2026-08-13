from __future__ import annotations

from factory.engine import SupabaseClient

_SCHEMA = "factu4all"
_FIELDS = [
    "source_system", "source_schema", "source_table", "source_id", "source_folio",
    "source_display_name", "legal_name", "tax_regime", "tax_zip_code",
    "cfdi_use_default", "billing_email", "billing_address", "status",
]
_PARTY_TYPES = {"customer", "supplier"}


class PartyManageService:
    def ejecutar(self, context: dict) -> dict:
        company_id = str(context.get("company_id") or context.get("empresa_id") or "").strip()
        if not company_id:
            return {"ok": False, "error": "company_id_requerido"}

        action = str(context.get("action") or "list").strip().lower()
        db = SupabaseClient({**context, "schema": _SCHEMA})

        if action == "list":
            return self._list(db, company_id, context.get("party_type"))

        rfc = str(context.get("rfc") or "").strip().upper()
        party_type = str(context.get("party_type") or "").strip().lower()
        if party_type not in _PARTY_TYPES:
            return {"ok": False, "error": "party_type debe ser customer|supplier"}
        if not rfc:
            return {"ok": False, "error": "rfc_requerido"}

        values = {key: context[key] for key in _FIELDS if key in context}

        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run: no se escribio en parties", "data": {"company_id": company_id, "rfc": rfc, "party_type": party_type, **values}}

        existing = db.rest_select(
            "parties",
            filters={"company_id": f"eq.{company_id}", "rfc": f"eq.{rfc}", "party_type": f"eq.{party_type}"},
            select="id",
            limit=1,
        )
        if not existing.get("ok"):
            return {"ok": False, "error": "db_query_failed", "data": {"detail": existing.get("error")}}

        if existing.get("data"):
            res = db.rest_update("parties", values, {"company_id": f"eq.{company_id}", "rfc": f"eq.{rfc}", "party_type": f"eq.{party_type}"})
        else:
            row = {
                "folio": f"PTY-{company_id}-{party_type}-{rfc}",
                "company_id": company_id,
                "rfc": rfc,
                "party_type": party_type,
                "legal_name": values.get("legal_name") or values.get("source_display_name") or rfc,
                "status": values.get("status") or "active",
                **{key: value for key, value in values.items() if key not in {"legal_name", "status"}},
            }
            res = db.rest_insert("parties", row)

        if not res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": res.get("error")}}
        return {"ok": True, "data": {"party": (res.get("data") or [{}])[0]}}

    def _list(self, db: SupabaseClient, company_id: str, party_type: str | None) -> dict:
        filters = {"company_id": f"eq.{company_id}"}
        if party_type:
            filters["party_type"] = f"eq.{str(party_type).strip().lower()}"
        res = db.rest_select("parties", filters=filters, select="*", order="created_at.desc")
        if not res.get("ok"):
            return {"ok": False, "error": "db_query_failed", "data": {"detail": res.get("error")}}
        return {"ok": True, "data": {"parties": res.get("data") or []}}
