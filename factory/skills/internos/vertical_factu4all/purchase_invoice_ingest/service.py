from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from factory.engine import SupabaseClient

_SCHEMA = "factu4all"
_BUCKET = "factu4all-documents"
_ENVIRONMENT = "production"
_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _runner():
    from factory.engine import SkillLoader, SkillRunner

    root = Path(__file__).resolve().parents[2]
    return SkillRunner(SkillLoader(internal_root=root))


class PurchaseInvoiceIngestService:
    def ejecutar(self, context: dict) -> dict:
        company_id = str(context.get("company_id") or context.get("empresa_id") or "").strip()
        xml = context.get("xml") or ""
        if not company_id:
            return {"ok": False, "error": "company_id_requerido"}
        if not xml:
            return {"ok": False, "error": "xml_requerido"}

        parse_res = _runner().run("vertical_sat/sat_cfdi_parser", {"xml": xml})
        if not parse_res.get("ok"):
            return {"ok": False, "error": "xml_parse_failed", "data": {"detail": parse_res.get("error")}}
        cfdi = (parse_res.get("data") or {}).get("cfdis", [{}])[0]
        uuid_val = cfdi.get("uuid") or ""
        if not uuid_val:
            return {"ok": False, "error": "xml_sin_uuid", "data": {"detail": "el XML no trae timbre fiscal (UUID)"}}
        if not cfdi.get("conceptos"):
            return {"ok": False, "error": "xml_sin_conceptos"}

        db = SupabaseClient({**context, "schema": _SCHEMA})
        dup = db.rest_select("cfdi_documents", filters={"company_id": f"eq.{company_id}", "uuid": f"eq.{uuid_val}", "direction": "eq.received"}, select="id,folio", limit=1)
        if dup.get("ok") and dup.get("data"):
            return {"ok": False, "error": "ya_importado", "data": {"detail": f"este UUID ya se importo (folio {dup['data'][0]['folio']})"}}

        dry_run = context.get("dry_run", True)
        preview_items = [self._preview_item(c) for c in cfdi["conceptos"]]
        if dry_run:
            return {
                "ok": True,
                "message": "dry_run: XML parseado, nada escrito",
                "data": {
                    "uuid": uuid_val,
                    "rfc_emisor": cfdi.get("rfc_emisor"),
                    "nombre_emisor": cfdi.get("nombre_emisor"),
                    "total": cfdi.get("total"),
                    "items": preview_items,
                },
            }

        supplier_res = _runner().run("vertical_factu4all/party_manage", {
            "action": "create", "company_id": company_id, "party_type": "supplier",
            "rfc": cfdi.get("rfc_emisor"), "legal_name": cfdi.get("nombre_emisor"), "dry_run": False,
        })
        if not supplier_res.get("ok"):
            return {"ok": False, "error": "supplier_resolve_failed", "data": {"detail": supplier_res.get("error")}}
        supplier = supplier_res["data"]["party"]

        doc_row = {
            "folio": f"CFDI-{company_id}-RECV-{uuid_val}",
            "company_id": company_id,
            "direction": "received",
            "cfdi_type": "ingreso" if cfdi.get("tipo_comprobante") == "I" else str(cfdi.get("tipo_comprobante") or ""),
            "business_effect": "purchase_expense",
            "source_system": "xml_compra",
            "source_type": "purchase_invoice",
            "source_id": uuid_val,
            "party_id": supplier.get("id"),
            "party_type": "supplier",
            "party_rfc_snapshot": cfdi.get("rfc_emisor"),
            "party_legal_name_snapshot": cfdi.get("nombre_emisor"),
            "payment_method": cfdi.get("metodo_pago"),
            "payment_form": cfdi.get("forma_pago"),
            "currency": cfdi.get("moneda") or "MXN",
            "environment": _ENVIRONMENT,
            "cfdi_folio": cfdi.get("folio"),
            "series": cfdi.get("serie"),
            "uuid": uuid_val,
            "status": "received",
            "subtotal": self._num(cfdi.get("subtotal")),
            "discount_total": self._num(cfdi.get("descuento")),
            "tax_total": self._num(cfdi.get("iva")),
            "total": self._num(cfdi.get("total")),
            "issued_at": cfdi.get("fecha_timbrado") or cfdi.get("fecha_emision"),
        }
        doc_res = db.rest_insert("cfdi_documents", doc_row)
        if not doc_res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": doc_res.get("error")}}
        cfdi_document = doc_res["data"][0]

        storage_path = self._store_xml(company_id, uuid_val, cfdi.get("xml_raw") or xml)
        if storage_path:
            db.rest_insert("document_files", {
                "folio": f"DOC-{company_id}-{uuid_val}-xml",
                "company_id": company_id,
                "cfdi_document_id": cfdi_document["id"],
                "uuid": uuid_val,
                "file_type": "xml",
                "storage_bucket": _BUCKET,
                "storage_path": storage_path,
                "content_type": "application/xml",
            })

        warehouse_id = self._default_warehouse(company_id)

        items_result = []
        for concepto in cfdi["conceptos"]:
            product, created = self._resolve_or_create_product(db, company_id, cfdi.get("rfc_emisor"), concepto)
            quantity = self._num(concepto.get("cantidad"))
            unit_price = self._num(concepto.get("valor_unitario"))
            discount = self._num(concepto.get("descuento"))
            tax_amount = self._num(concepto.get("iva_concepto"))
            subtotal = self._num(concepto.get("importe"))

            db.rest_insert("cfdi_item_movements", {
                "folio": f"{cfdi_document['folio']}-{product['id'][:8]}",
                "company_id": company_id,
                "cfdi_document_id": cfdi_document["id"],
                "uuid": uuid_val,
                "movement_direction": "in",
                "document_direction": "received",
                "business_effect": "purchase_expense",
                "party_id": supplier.get("id"),
                "party_type": "supplier",
                "product_id": product["id"],
                "warehouse_id": warehouse_id,
                "source_product_key": product.get("source_product_key"),
                "source_product_name": concepto.get("descripcion"),
                "fiscal_product_name_snapshot": product.get("fiscal_product_name"),
                "sat_product_key_snapshot": product.get("sat_product_key"),
                "sat_unit_key_snapshot": product.get("sat_unit_key"),
                "tax_object_snapshot": product.get("tax_object"),
                "quantity": quantity,
                "unit_price": unit_price,
                "subtotal": subtotal,
                "discount_amount": discount,
                "tax_amount": tax_amount,
                "total": round(subtotal - discount + tax_amount, 2),
                "environment": _ENVIRONMENT,
                "issued_at": doc_row["issued_at"],
            })
            if warehouse_id:
                self._trigger_recalculate(company_id, product["id"], warehouse_id, _ENVIRONMENT, doc_row["issued_at"])
            items_result.append({
                "descripcion": concepto.get("descripcion"),
                "cantidad": quantity,
                "product_id": product["id"],
                "product_created": created,
                "sat_product_key": product.get("sat_product_key"),
            })

        return {"ok": True, "data": {"cfdi_document": cfdi_document, "supplier": supplier, "items": items_result}}

    def _preview_item(self, concepto: dict) -> dict:
        return {
            "descripcion": concepto.get("descripcion"),
            "cantidad": concepto.get("cantidad"),
            "clave_prod_serv": concepto.get("clave_prod_serv"),
            "clave_unidad": concepto.get("clave_unidad"),
        }

    def _resolve_or_create_product(self, db: SupabaseClient, company_id: str, supplier_rfc: str, concepto: dict) -> tuple[dict, bool]:
        supplier_key = str(concepto.get("no_identificacion") or concepto.get("clave_prod_serv") or "").strip()
        mapping_res = db.rest_select(
            "supplier_product_mappings",
            filters={"company_id": f"eq.{company_id}", "supplier_rfc": f"eq.{supplier_rfc}", "supplier_product_key": f"eq.{supplier_key}"},
            select="factu4all_product_id",
            limit=1,
        )
        mapped_id = None
        if mapping_res.get("ok") and mapping_res.get("data"):
            mapped_id = mapping_res["data"][0].get("factu4all_product_id")
        if mapped_id:
            prod_res = db.rest_select("products", filters={"id": f"eq.{mapped_id}"}, select="*", limit=1)
            if prod_res.get("ok") and prod_res.get("data"):
                return prod_res["data"][0], False

        sat_key = str(concepto.get("clave_prod_serv") or "").strip() or "sinclave"
        source_key = "compra:" + _SLUG_RE.sub("-", (supplier_key or concepto.get("descripcion") or sat_key).lower()).strip("-")
        existing = db.rest_select("products", filters={"company_id": f"eq.{company_id}", "source_product_key": f"eq.{source_key}"}, select="*", limit=1)
        if existing.get("ok") and existing.get("data"):
            product = existing["data"][0]
        else:
            row = {
                "folio": f"PRD-{company_id}-{source_key}",
                "company_id": company_id,
                "source_system": "xml_compra",
                "source_product_key": source_key,
                "source_product_name": concepto.get("descripcion"),
                "fiscal_product_name": concepto.get("descripcion") or sat_key,
                "sat_product_key": sat_key,
                "sat_unit_key": concepto.get("clave_unidad") or "",
                "sat_unit_name": concepto.get("unidad") or "",
                "tax_object": concepto.get("objeto_imp") or "02",
                "status": "revisar",
            }
            ins = db.rest_insert("products", row)
            product = (ins.get("data") or [row])[0] if ins.get("ok") else row

        db.rest_insert("supplier_product_mappings", {
            "folio": f"SPM-{company_id}-{supplier_rfc}-{source_key}",
            "company_id": company_id,
            "supplier_rfc": supplier_rfc,
            "supplier_product_key": supplier_key,
            "supplier_product_description": concepto.get("descripcion"),
            "sat_product_key": sat_key,
            "sat_unit_key": concepto.get("clave_unidad") or "",
            "factu4all_product_id": product.get("id"),
            "status": "auto_mapped",
        })
        return product, True

    def _default_warehouse(self, company_id: str) -> str:
        res = _runner().run("vertical_factu4all/warehouse_manage", {"action": "ensure_default", "company_id": company_id})
        if not res.get("ok"):
            return ""
        return (res.get("data") or {}).get("warehouse", {}).get("id") or ""

    def _trigger_recalculate(self, company_id: str, product_id: str, warehouse_id: str, environment: str, issued_at: str | None) -> None:
        issued_at = issued_at or datetime.now(timezone.utc).isoformat()
        try:
            year, month = int(issued_at[0:4]), int(issued_at[5:7])
        except (ValueError, IndexError):
            now = datetime.now(timezone.utc)
            year, month = now.year, now.month
        _runner().run("vertical_factu4all/inventory_recalculate", {
            "company_id": company_id, "product_id": product_id, "warehouse_id": warehouse_id,
            "environment": environment, "from_year": year, "from_month": month, "dry_run": False,
        })

    def _store_xml(self, company_id: str, uuid_val: str, xml: str) -> str:
        import base64

        now = datetime.now(timezone.utc)
        path = f"{company_id}/{_ENVIRONMENT}/received/{now:%Y}/{now:%m}/{uuid_val}.xml"
        res = _runner().run("vertical_supabase/supabase_storage_upload", {
            "bucket": _BUCKET, "path": path,
            "content_b64": base64.b64encode(xml.encode("utf-8")).decode(),
            "content_type": "application/xml",
        })
        return path if res.get("ok") else ""

    def _num(self, value) -> float:
        try:
            return float(value or 0)
        except Exception:
            return 0.0
