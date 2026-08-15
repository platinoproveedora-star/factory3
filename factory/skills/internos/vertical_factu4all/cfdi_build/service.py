from __future__ import annotations

from pathlib import Path

from factory.engine import SupabaseClient

_SCHEMA = "factu4all"
_SOURCE_FIELDS = ["source_system", "source_schema", "source_table", "source_type", "source_id", "source_folio"]


def _runner():
    from factory.engine import SkillLoader, SkillRunner

    root = Path(__file__).resolve().parents[2]
    return SkillRunner(SkillLoader(internal_root=root))


class CfdiBuildService:
    def ejecutar(self, context: dict) -> dict:
        company_id = str(context.get("company_id") or context.get("empresa_id") or "").strip()
        items = context.get("items") if isinstance(context.get("items"), list) else []
        if not company_id:
            return {"ok": False, "error": "company_id_requerido"}
        if not items:
            return {"ok": False, "error": "items_requerido"}

        db = SupabaseClient({**context, "schema": _SCHEMA})
        dry_run = context.get("dry_run", True)

        issuer = self._resolve_issuer(db, company_id, context)
        if not issuer.get("ok"):
            return issuer
        issuer_profile = issuer["data"]

        party = self._resolve_party(db, company_id, context)
        if not party.get("ok"):
            return party
        party_row = party["data"]

        totals = self._compute_totals(items, issuer_profile.get("iva_rate") if isinstance(issuer_profile, dict) else None)

        company_settings = self._resolve_company_settings(company_id)

        cfdi_type = str(context.get("cfdi_type") or "ingreso").strip().lower()
        environment = str(
            context.get("environment") or issuer_profile.get("environment") or company_settings.get("default_environment") or "sandbox"
        ).strip().lower()
        pac_provider = issuer_profile.get("pac_provider") or company_settings.get("default_pac_provider")

        folio_res = _runner().run(
            "vertical_factu4all/folio_series_manage",
            {
                "action": "next",
                "company_id": company_id,
                "cfdi_type": cfdi_type,
                "series": context.get("series"),
                "environment": environment,
                "dry_run": dry_run,
            },
        )
        if not folio_res.get("ok"):
            return {"ok": False, "error": "folio_series_failed", "data": {"detail": folio_res.get("error")}}
        folio_data = folio_res.get("data") or {}
        series = folio_data.get("series")
        cfdi_folio = folio_data.get("cfdi_folio")

        row = {
            "company_id": company_id,
            "direction": "issued",
            "cfdi_type": cfdi_type,
            "business_effect": context.get("business_effect") or "sale",
            "issuer_profile_id": issuer_profile.get("id"),
            "issuer_rfc_snapshot": issuer_profile.get("rfc"),
            "issuer_legal_name_snapshot": issuer_profile.get("legal_name"),
            "party_id": party_row.get("id"),
            "party_type": party_row.get("party_type"),
            "party_rfc_snapshot": party_row.get("rfc"),
            "party_legal_name_snapshot": party_row.get("legal_name"),
            "payment_method": context.get("payment_method"),
            "payment_form": context.get("payment_form"),
            "currency": context.get("currency") or "MXN",
            "pac_provider": pac_provider,
            "environment": environment,
            "series": series,
            "cfdi_folio": cfdi_folio,
            "status": "draft",
            **totals,
            **{key: context.get(key) for key in _SOURCE_FIELDS if context.get(key)},
        }
        row.setdefault("source_system", "factu4all")
        row.setdefault("source_type", "direct_invoice")

        preview = {**row, "issuer_rfc": issuer_profile.get("rfc"), "items": items}
        if dry_run:
            return {"ok": True, "message": "dry_run: folio no reservado, cfdi_documents no escrito", "data": {"cfdi_document": preview}}

        row["folio"] = f"CFDI-{company_id}-{cfdi_folio}"
        res = db.rest_insert("cfdi_documents", row)
        if not res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": res.get("error")}}
        cfdi_document = (res.get("data") or [row])[0]

        movements = self._build_item_movements(db, company_id, cfdi_document, party_row, items)
        if movements:
            mv_res = db.rest_insert("cfdi_item_movements", movements)
            if not mv_res.get("ok"):
                return {"ok": False, "error": "db_persistence_failed", "data": {"detail": mv_res.get("error"), "cfdi_document": cfdi_document}}

        return {"ok": True, "data": {"cfdi_document": cfdi_document, "items": items}}

    def _build_item_movements(self, db: SupabaseClient, company_id: str, cfdi_document: dict, party_row: dict, items: list) -> list:
        default_rate = 0.16
        rows = []
        for index, item in enumerate(items, start=1):
            product = self._resolve_product(db, company_id, item)
            quantity = float(item.get("quantity") or 0)
            unit_price = float(item.get("unit_price") or 0)
            discount = float(item.get("discount_amount") or 0)
            iva_rate = float(item.get("iva_rate")) if item.get("iva_rate") not in (None, "") else default_rate
            line_subtotal = quantity * unit_price
            taxable = max(line_subtotal - discount, 0)
            tax_amount = round(taxable * iva_rate, 2)
            rows.append({
                "folio": f"{cfdi_document['folio']}-{index}",
                "company_id": company_id,
                "cfdi_document_id": cfdi_document["id"],
                "movement_direction": "out",
                "document_direction": cfdi_document.get("direction"),
                "business_effect": cfdi_document.get("business_effect"),
                "source_document_id": cfdi_document.get("source_id"),
                "source_document_folio": cfdi_document.get("source_folio"),
                "party_id": party_row.get("id"),
                "party_type": party_row.get("party_type"),
                "product_id": (product or {}).get("id"),
                "source_product_id": item.get("source_product_id") or (product or {}).get("source_id"),
                "source_product_key": item.get("source_product_key") or (product or {}).get("source_product_key"),
                "source_product_name": item.get("source_product_name") or (product or {}).get("source_product_name"),
                "fiscal_product_name_snapshot": (product or {}).get("fiscal_product_name") or item.get("description"),
                "sat_product_key_snapshot": (product or {}).get("sat_product_key") or item.get("sat_product_key"),
                "sat_unit_key_snapshot": (product or {}).get("sat_unit_key") or item.get("sat_unit_key"),
                "sat_group_key_snapshot": (product or {}).get("sat_group_key") or item.get("sat_group_key"),
                "tax_object_snapshot": (product or {}).get("tax_object") or item.get("tax_object"),
                "quantity": quantity,
                "unit_price": unit_price,
                "subtotal": round(line_subtotal, 2),
                "discount_amount": round(discount, 2),
                "tax_amount": tax_amount,
                "total": round(taxable + tax_amount, 2),
            })
        return rows

    def _resolve_product(self, db: SupabaseClient, company_id: str, item: dict) -> dict | None:
        product_id = str(item.get("product_id") or "").strip()
        source_product_key = str(item.get("source_product_key") or "").strip()
        filters = {"company_id": f"eq.{company_id}"}
        if product_id:
            filters["id"] = f"eq.{product_id}"
        elif source_product_key:
            filters["source_product_key"] = f"eq.{source_product_key}"
        else:
            return None
        res = db.rest_select("products", filters=filters, select="*", limit=1)
        rows = res.get("data") or [] if res.get("ok") else []
        return rows[0] if rows else None

    def _resolve_company_settings(self, company_id: str) -> dict:
        res = _runner().run("vertical_factu4all/company_settings_manage", {"action": "get", "company_id": company_id})
        if not res.get("ok"):
            return {}
        return (res.get("data") or {}).get("settings") or {}

    def _resolve_issuer(self, db: SupabaseClient, company_id: str, context: dict) -> dict:
        issuer_profile_id = str(context.get("issuer_profile_id") or "").strip()
        rfc = str(context.get("issuer_rfc") or "").strip().upper()
        filters = {"company_id": f"eq.{company_id}"}
        if issuer_profile_id:
            filters["id"] = f"eq.{issuer_profile_id}"
        elif rfc:
            filters["rfc"] = f"eq.{rfc}"
        else:
            return {"ok": False, "error": "issuer_profile_id_o_issuer_rfc_requerido"}
        res = db.rest_select("issuer_profiles", filters=filters, select="*", limit=1)
        if not res.get("ok"):
            return {"ok": False, "error": "db_query_failed", "data": {"detail": res.get("error")}}
        rows = res.get("data") or []
        if not rows:
            return {"ok": False, "error": "issuer_profile_not_found"}
        return {"ok": True, "data": rows[0]}

    def _resolve_party(self, db: SupabaseClient, company_id: str, context: dict) -> dict:
        party_id = str(context.get("party_id") or "").strip()
        rfc = str(context.get("party_rfc") or "").strip().upper()
        party_type = str(context.get("party_type") or "customer").strip().lower()
        filters = {"company_id": f"eq.{company_id}"}
        if party_id:
            filters["id"] = f"eq.{party_id}"
        elif rfc:
            filters["rfc"] = f"eq.{rfc}"
            filters["party_type"] = f"eq.{party_type}"
        else:
            return {"ok": False, "error": "party_id_o_party_rfc_requerido"}
        res = db.rest_select("parties", filters=filters, select="*", limit=1)
        if not res.get("ok"):
            return {"ok": False, "error": "db_query_failed", "data": {"detail": res.get("error")}}
        rows = res.get("data") or []
        if not rows:
            return {"ok": False, "error": "party_not_found"}
        return {"ok": True, "data": rows[0]}

    def _compute_totals(self, items: list, default_iva_rate) -> dict:
        default_rate = float(default_iva_rate) if default_iva_rate not in (None, "") else 0.16
        subtotal = 0.0
        discount_total = 0.0
        tax_total = 0.0
        for item in items:
            quantity = float(item.get("quantity") or 0)
            unit_price = float(item.get("unit_price") or 0)
            discount = float(item.get("discount_amount") or 0)
            iva_rate = float(item.get("iva_rate")) if item.get("iva_rate") not in (None, "") else default_rate
            line_subtotal = quantity * unit_price
            taxable = max(line_subtotal - discount, 0)
            subtotal += line_subtotal
            discount_total += discount
            tax_total += taxable * iva_rate
        total = subtotal - discount_total + tax_total
        return {
            "subtotal": round(subtotal, 2),
            "discount_total": round(discount_total, 2),
            "tax_total": round(tax_total, 2),
            "total": round(total, 2),
        }
