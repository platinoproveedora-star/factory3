from __future__ import annotations

from pathlib import Path

from factory.engine import SupabaseClient

_SCHEMA = "factu4all"


def _runner():
    from factory.engine import SkillLoader, SkillRunner

    root = Path(__file__).resolve().parents[2]
    return SkillRunner(SkillLoader(internal_root=root))


class PurchaseOrderCreateService:
    def ejecutar(self, context: dict) -> dict:
        company_id = str(context.get("company_id") or context.get("empresa_id") or "").strip()
        supplier_rfc = str(context.get("supplier_rfc") or "").strip().upper()
        source_system = str(context.get("source_system") or "").strip()
        source_id = str(context.get("source_id") or "").strip()
        items = context.get("items") if isinstance(context.get("items"), list) else []
        if not company_id or not supplier_rfc or not source_system or not source_id:
            return {"ok": False, "error": "missing_fields", "data": {"missing": ["company_id", "supplier_rfc", "source_system", "source_id"]}}
        if not items:
            return {"ok": False, "error": "items_requerido"}

        folio = f"PO-{company_id}-{source_system}-{source_id}"
        db = SupabaseClient({**context, "schema": _SCHEMA})

        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run: no se escribio", "data": {"folio": folio, "items": items}}

        existing = db.rest_select("cfdi_documents", filters={"company_id": f"eq.{company_id}", "folio": f"eq.{folio}"}, select="*", limit=1)
        if existing.get("ok") and existing.get("data"):
            return {"ok": True, "message": "ya existia esta orden de compra", "data": {"cfdi_document": existing["data"][0]}}

        supplier_res = _runner().run("vertical_factu4all/party_manage", {
            "action": "create", "company_id": company_id, "party_type": "supplier",
            "rfc": supplier_rfc, "legal_name": context.get("supplier_name") or supplier_rfc, "dry_run": False,
        })
        if not supplier_res.get("ok"):
            return {"ok": False, "error": "supplier_resolve_failed", "data": {"detail": supplier_res.get("error")}}
        supplier = supplier_res["data"]["party"]

        estimated_total = round(sum(float(item.get("quantity") or 0) * float(item.get("estimated_unit_price") or 0) for item in items), 2)

        row = {
            "folio": folio,
            "company_id": company_id,
            "direction": "received",
            "cfdi_type": "ingreso",
            "business_effect": "purchase_expense",
            "source_system": source_system,
            "source_type": "purchase_order",
            "source_id": source_id,
            "source_folio": context.get("source_folio"),
            "party_id": supplier.get("id"),
            "party_type": "supplier",
            "party_rfc_snapshot": supplier_rfc,
            "party_legal_name_snapshot": supplier.get("legal_name"),
            "currency": context.get("currency") or "MXN",
            "environment": "production",
            "status": "pending_xml",
            "subtotal": estimated_total,
            "total": estimated_total,
            "metadata": {"items": items, "expected_date": context.get("expected_date")},
        }
        res = db.rest_insert("cfdi_documents", row)
        if not res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": res.get("error")}}
        return {"ok": True, "data": {"cfdi_document": res["data"][0], "supplier": supplier}}
