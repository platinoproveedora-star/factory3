from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import SupabaseClient, money, resolve_billing_context, today_iso  # noqa: E402


class ErpBillingDashboardDataService:
    def ejecutar(self, context: dict) -> dict:
        ctx_result = resolve_billing_context(context)
        if not ctx_result.get("ok"):
            return ctx_result
        ctx = ctx_result["data"]
        limit = min(int(context.get("limit") or 50), 200)
        db = SupabaseClient(ctx)
        payments_result = db.rest_select(
            "billing_payments",
            filters={"empresa_id": ctx["company_id"]},
            select="id,folio,collection_folio,customer_id,customer_name,payment_method,amount,unapplied_amount,payment_date,source_money_account_id,destination_money_account_id,bank_name,reference,tracking_key,receipt_file_url,receipt_file_path,receipt_file_bucket,status,validation_status,ocr_status,metadata,created_at",
            order="payment_date.desc,created_at.desc",
            limit=limit,
        )
        if not payments_result.get("ok"):
            return payments_result
        applications_result = db.rest_select(
            "billing_payment_applications",
            filters={"empresa_id": ctx["company_id"]},
            select="id,folio,payment_id,payment_folio,sales_folio,amount_applied,status,metadata,created_at",
            order="created_at.desc",
            limit=limit,
        )
        if not applications_result.get("ok"):
            return applications_result
        folios_result = db.rest_select(
            "billing_collection_folios",
            filters={"empresa_id": ctx["company_id"]},
            select="id,folio,sales_folio,customer_name,expected_amount,collected_amount,balance_amount,status,collector_name,due_date,payment_id,metadata,created_at",
            order="created_at.desc",
            limit=limit,
        )
        if not folios_result.get("ok"):
            return folios_result
        accounts_result = db.rest_select(
            "billing_money_accounts",
            filters={"empresa_id": ctx["company_id"], "status": "active"},
            select="id,folio,account_type,account_name,currency,current_balance,responsible_user,status",
            order="account_name.asc",
            limit=200,
        )
        if not accounts_result.get("ok"):
            return accounts_result

        payments = payments_result.get("data") or []
        applications = applications_result.get("data") or []
        folios = folios_result.get("data") or []
        accounts = accounts_result.get("data") or []
        today = today_iso()
        collected_today = sum(money(p.get("amount")) for p in payments if str(p.get("payment_date") or "") == today and p.get("status") != "cancelado")
        unapplied_total = sum(money(p.get("unapplied_amount")) for p in payments if p.get("status") in {"sin_aplicar", "capturado", "parcial"})
        receivable_total = sum(money(f.get("balance_amount")) for f in folios if f.get("status") not in {"pagada", "cancelada"})
        pending_folios = [f for f in folios if f.get("status") in {"emitido", "parcial"}][:20]
        pending_validation = [p for p in payments if p.get("validation_status") in {"pending", "requiere_revision"} or p.get("ocr_status") == "pending"][:20]
        return {
            "ok": True,
            "data": {
                "kpis": {
                    "collected_today": round(collected_today, 2),
                    "unapplied_total": round(unapplied_total, 2),
                    "receivable_total": round(receivable_total, 2),
                    "active_accounts": len(accounts),
                    "pending_folios": len(pending_folios),
                    "pending_validation": len(pending_validation),
                },
                "payments": payments,
                "payment_applications": applications,
                "collection_folios": folios,
                "money_accounts": accounts,
                "work_queue": {
                    "pending_folios": pending_folios,
                    "pending_validation": pending_validation,
                },
            },
        }
