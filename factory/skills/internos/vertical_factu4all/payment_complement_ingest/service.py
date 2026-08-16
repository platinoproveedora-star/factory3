from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from factory.engine import SupabaseClient

_SCHEMA = "factu4all"
_BUCKET = "factu4all-documents"
_ENVIRONMENT = "production"


def _runner():
    from factory.engine import SkillLoader, SkillRunner

    root = Path(__file__).resolve().parents[2]
    return SkillRunner(SkillLoader(internal_root=root))


class PaymentComplementIngestService:
    def ejecutar(self, context: dict) -> dict:
        company_id = str(context.get("company_id") or "").strip()
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
            return {"ok": False, "error": "xml_sin_uuid"}
        if cfdi.get("tipo_comprobante") != "P":
            return {"ok": False, "error": "no_es_complemento_de_pago", "data": {"detail": "este XML no es un REP (TipoDeComprobante != P) — usa purchase_invoice_ingest"}}
        doctos = cfdi.get("pago_doctos_relacionados") or []
        if not doctos:
            return {"ok": False, "error": "rep_sin_doctos_relacionados"}

        db = SupabaseClient({**context, "schema": _SCHEMA})
        dup = db.rest_select("cfdi_documents", filters={"company_id": f"eq.{company_id}", "uuid": f"eq.{uuid_val}", "direction": "eq.received"}, select="id,folio", limit=1)
        if dup.get("ok") and dup.get("data"):
            return {"ok": False, "error": "ya_importado", "data": {"detail": f"este REP ya se importo (folio {dup['data'][0]['folio']})"}}

        dry_run = context.get("dry_run", True)
        total_pagado = round(sum(self._num(d.get("imp_pagado")) for d in doctos), 2)
        if dry_run:
            return {"ok": True, "message": "dry_run: REP parseado, nada escrito", "data": {"uuid": uuid_val, "rfc_emisor": cfdi.get("rfc_emisor"), "doctos_relacionados": doctos, "total_pagado": total_pagado}}

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
            "cfdi_type": "pago",
            "business_effect": "payment_complement",
            "classification_group": "complemento_pago",
            "uso_cfdi": cfdi.get("uso_cfdi"),
            "source_system": "xml_rep",
            "source_type": "payment_complement",
            "source_id": uuid_val,
            "party_id": supplier.get("id"),
            "party_type": "supplier",
            "party_rfc_snapshot": cfdi.get("rfc_emisor"),
            "party_legal_name_snapshot": cfdi.get("nombre_emisor"),
            "currency": cfdi.get("moneda") or "MXN",
            "environment": _ENVIRONMENT,
            "cfdi_folio": cfdi.get("folio"),
            "series": cfdi.get("serie"),
            "uuid": uuid_val,
            "status": "received",
            "subtotal": 0,
            "tax_total": 0,
            "total": total_pagado,
            "issued_at": cfdi.get("fecha_timbrado") or cfdi.get("fecha_emision"),
        }
        doc_res = db.rest_insert("cfdi_documents", doc_row)
        if not doc_res.get("ok") or not doc_res.get("data"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": doc_res.get("error")}}
        payment_document = doc_res["data"][0]

        storage_path = self._store_xml(company_id, uuid_val, cfdi.get("xml_raw") or xml)
        if storage_path:
            db.rest_insert("document_files", {
                "folio": f"DOC-{company_id}-{uuid_val}-xml",
                "company_id": company_id,
                "cfdi_document_id": payment_document["id"],
                "uuid": uuid_val,
                "file_type": "xml",
                "storage_bucket": _BUCKET,
                "storage_path": storage_path,
                "content_type": "application/xml",
            })

        matched, unmatched = [], []
        for docto in doctos:
            related_uuid = docto.get("uuid") or ""
            imp_pagado = self._num(docto.get("imp_pagado"))
            rel_res = db.rest_select(
                "cfdi_documents",
                filters={"company_id": f"eq.{company_id}", "uuid": f"eq.{related_uuid}", "direction": "eq.received"},
                select="id,folio", limit=1,
            )
            related = (rel_res.get("data") or [None])[0] if rel_res.get("ok") else None
            if not related:
                unmatched.append({"uuid": related_uuid, "imp_pagado": imp_pagado})
                continue

            db.rest_insert("payment_complement_links", {
                "company_id": company_id,
                "payment_document_id": payment_document["id"],
                "related_document_id": related["id"],
                "imp_pagado": imp_pagado,
            })
            db.rest_update(
                "cfdi_documents",
                values={"payment_status": "paid_confirmed", "rep_received_at": datetime.now(timezone.utc).isoformat()},
                filters={"id": f"eq.{related['id']}"},
            )
            matched.append({"uuid": related_uuid, "folio": related["folio"], "imp_pagado": imp_pagado})

        return {"ok": True, "data": {"payment_document": payment_document, "matched": matched, "unmatched": unmatched}}

    def _store_xml(self, company_id: str, uuid_val: str, xml: str) -> str:
        import base64

        now = datetime.now(timezone.utc)
        path = f"{company_id}/{_ENVIRONMENT}/payments/{now:%Y}/{now:%m}/{uuid_val}.xml"
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
