from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import SupabaseClient, blank, fetch_one, money, resolve_billing_context, sales_context  # noqa: E402


_ROOT = Path(__file__).resolve().parents[1]
_METHOD_MAP = {
    "cash": "cash",
    "efectivo": "cash",
    "transfer": "transfer",
    "transferencia": "transfer",
    "deposit": "deposit",
    "deposito": "deposit",
    "depósito": "deposit",
    "card": "card",
    "tarjeta": "card",
    "check": "check",
    "cheque": "check",
    "other": "other",
    "otro": "other",
}


def _text(value: Any) -> str:
    return str(value or "").strip()


class ErpBillingPaymentCreateAndApplyService:
    def ejecutar(self, context: dict) -> dict:
        ctx_result = resolve_billing_context(context)
        if not ctx_result.get("ok"):
            return ctx_result
        ctx = ctx_result["data"]
        sales_ctx_result = sales_context(ctx)
        if not sales_ctx_result.get("ok"):
            return sales_ctx_result
        sales_ctx = sales_ctx_result["data"]

        payment_method = self._method(context.get("payment_method"))
        amount = money(context.get("amount"))
        destination_account_id = blank(context.get("destination_money_account_id"))
        applications = self._applications(context.get("applications"))

        if not payment_method:
            return {"ok": False, "error": "payment_method invalido"}
        if amount <= 0:
            return {"ok": False, "error": "amount debe ser mayor a 0"}
        if not destination_account_id:
            return {"ok": False, "error": "destination_money_account_id requerido"}
        if not applications:
            return {"ok": False, "error": "applications requerido"}

        documents = self._load_documents(sales_ctx, applications)
        if not documents.get("ok"):
            return documents
        docs = documents["data"]["documents"]
        validation = self._validate_applications(ctx, context, docs, applications, amount)
        if not validation.get("ok"):
            return validation
        normalized_apps = validation["data"]["applications"]
        customer = validation["data"]["customer"]
        total_applied = validation["data"]["total_applied"]

        payment_payload = {
            **context,
            "payment_method": payment_method,
            "amount": amount,
            "destination_money_account_id": destination_account_id,
            "customer_id": customer.get("customer_id"),
            "customer_name": customer.get("customer_name"),
            "metadata": {
                **(context.get("metadata") if isinstance(context.get("metadata"), dict) else {}),
                "payment_mode": "multi_remision",
                "applications_count": len(normalized_apps),
                "total_applied_requested": total_applied,
            },
            "dry_run": context.get("dry_run", True),
        }
        if context.get("dry_run", True):
            return {
                "ok": True,
                "message": "dry_run: no se creo pago ni aplicaciones",
                "data": {
                    "payment_preview": payment_payload,
                    "applications_preview": normalized_apps,
                    "unapplied_amount": max(amount - total_applied, 0),
                },
            }

        create_result = self._payment_create_service().ejecutar(payment_payload)
        if not create_result.get("ok"):
            return create_result
        payment = (create_result.get("data") or {}).get("payment") or {}

        applied = []
        for app in normalized_apps:
            result = self._payment_apply_service().ejecutar({
                **context,
                "payment_id": payment.get("id"),
                "sales_document_id": app["sales_document_id"],
                "amount_applied": app["amount_applied"],
                "metadata": {
                    "payment_mode": "multi_remision",
                    "created_by_skill": "erp_billing_payment_create_and_apply",
                },
                "dry_run": False,
            })
            if not result.get("ok"):
                return {
                    "ok": False,
                    "error": result.get("error") or "fallo aplicando pago",
                    "data": {"payment": payment, "applications_saved": applied, "failed_application": app},
                }
            applied.append(result.get("data"))

        refreshed = fetch_one(SupabaseClient(ctx), "billing_payments", {"id": payment.get("id")})
        return {"ok": True, "data": {"payment": refreshed or payment, "applications": applied}}

    def _method(self, value: Any) -> str:
        return _METHOD_MAP.get(_text(value).lower(), "")

    def _applications(self, raw: Any) -> list[dict]:
        if not isinstance(raw, list):
            return []
        rows = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            amount = money(item.get("amount_applied") if item.get("amount_applied") is not None else item.get("amount"))
            sales_document_id = blank(item.get("sales_document_id") or item.get("document_id"))
            sales_folio = blank(item.get("sales_folio") or item.get("document_folio"))
            if amount > 0 and (sales_document_id or sales_folio):
                rows.append({"sales_document_id": sales_document_id, "sales_folio": sales_folio, "amount_applied": amount})
        return rows

    def _load_documents(self, sales_ctx: dict, applications: list[dict]) -> dict:
        docs = []
        db = SupabaseClient(sales_ctx)
        for app in applications:
            filters = {"id": app["sales_document_id"]} if app.get("sales_document_id") else {"folio": app["sales_folio"]}
            doc = fetch_one(
                db,
                "sales_documents",
                filters,
                "id,folio,document_type,customer_id,customer_name_snapshot,total,paid_total,balance_total,status",
            )
            if not doc:
                return {"ok": False, "error": "remision no encontrada", "data": {"application": app}}
            docs.append(doc)
        return {"ok": True, "data": {"documents": docs}}

    def _validate_applications(self, ctx: dict, context: dict, docs: list[dict], applications: list[dict], amount: float) -> dict:
        customer_key = ""
        customer = {"customer_id": blank(context.get("customer_id")), "customer_name": blank(context.get("customer_name"))}
        normalized = []
        total_applied = 0.0
        seen: set[str] = set()
        by_doc = {str(doc["id"]): doc for doc in docs}

        for app in applications:
            doc = by_doc.get(str(app.get("sales_document_id"))) if app.get("sales_document_id") else next((row for row in docs if row.get("folio") == app.get("sales_folio")), None)
            if not doc:
                return {"ok": False, "error": "remision no encontrada"}
            if str(doc.get("document_type") or "").strip().lower() != "remision":
                return {"ok": False, "error": "solo se pueden aplicar pagos a remisiones"}
            if str(doc.get("status") or "").strip().lower() == "cancelada":
                return {"ok": False, "error": f"remision cancelada: {doc.get('folio')}"}
            if str(doc["id"]) in seen:
                return {"ok": False, "error": f"remision duplicada: {doc.get('folio')}"}
            seen.add(str(doc["id"]))

            key = str(doc.get("customer_id") or doc.get("customer_name_snapshot") or "").strip()
            if customer_key and key and key != customer_key:
                return {"ok": False, "error": "todas las remisiones deben ser del mismo cliente"}
            customer_key = customer_key or key
            customer["customer_id"] = customer["customer_id"] or blank(doc.get("customer_id"))
            customer["customer_name"] = customer["customer_name"] or blank(doc.get("customer_name_snapshot"))

            current_balance = money(doc.get("balance_total") if doc.get("balance_total") is not None else doc.get("total"))
            applied = money(app.get("amount_applied"))
            if applied > current_balance:
                return {"ok": False, "error": f"importe excede saldo de {doc.get('folio')}"}
            total_applied = money(total_applied + applied)
            normalized.append({"sales_document_id": doc["id"], "sales_folio": doc.get("folio"), "amount_applied": applied})

        if total_applied <= 0:
            return {"ok": False, "error": "total aplicado debe ser mayor a 0"}
        if total_applied > amount:
            return {"ok": False, "error": "total aplicado excede el importe del pago"}
        return {"ok": True, "data": {"applications": normalized, "customer": customer, "total_applied": total_applied}}

    def _payment_create_service(self):
        return self._load_service("erp_billing_payment_create")

    def _payment_apply_service(self):
        return self._load_service("erp_billing_payment_apply")

    def _load_service(self, name: str):
        path = _ROOT / name / "service.py"
        spec = importlib.util.spec_from_file_location(f"{name}_service", path)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        class_name = "".join(part.capitalize() for part in name.split("_")) + "Service"
        return getattr(module, class_name)()
