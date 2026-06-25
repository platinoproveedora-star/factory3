from __future__ import annotations
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import SupabaseClient, money, resolve_billing_context, sales_context  # noqa: E402


class ErpBillingCashCutDataService:
    def ejecutar(self, context: dict) -> dict:
        ctx_result = resolve_billing_context(context)
        if not ctx_result.get("ok"):
            return ctx_result
        ctx = ctx_result["data"]

        cut_date = str(context.get("cut_date") or date.today().isoformat())
        billing_db = SupabaseClient(ctx)

        # Pagos recibidos HOY
        pagos_hoy_r = billing_db.rest_select(
            "billing_payments",
            filters={"payment_date": f"eq.{cut_date}"},
            select="id,folio,customer_name,amount,payment_method,destination_money_account_id,confirmation_status,status",
            limit=500,
        )
        pagos_hoy = pagos_hoy_r.get("data") or [] if pagos_hoy_r.get("ok") else []

        # Remisiones creadas HOY
        remisiones_hoy = []
        sales_ctx_result = sales_context(ctx)
        if sales_ctx_result.get("ok"):
            sales_ctx = sales_ctx_result["data"]
            rem_r = SupabaseClient(sales_ctx).rest_select(
                "sales_documents",
                filters={"document_date": f"eq.{cut_date}"},
                select="id,folio,customer_name_snapshot,total,paid_total,balance_total,status",
                limit=500,
            )
            remisiones_hoy = rem_r.get("data") or [] if rem_r.get("ok") else []

        # CXC pendientes de fechas anteriores
        cxc_r = SupabaseClient(sales_ctx).rest_select(
            "sales_documents",
            filters={"status": "neq.cancelada"},
            select="id,folio,document_date,customer_name_snapshot,total,paid_total,balance_total,status",
            limit=500,
            order="document_date.asc",
        ) if sales_ctx_result.get("ok") else {"ok": False}
        cxc_all = cxc_r.get("data") or [] if cxc_r.get("ok") else []
        cxc_anteriores = [r for r in cxc_all if r.get("document_date") and r["document_date"] < cut_date and money(r.get("balance_total") if r.get("balance_total") is not None else r.get("total")) > 0]
        for r in cxc_anteriores:
            r["dias_vencido"] = (date.today() - date.fromisoformat(r["document_date"])).days

        # Transferencias por confirmar (acumuladas de todos los dias)
        por_confirmar_r = billing_db.rest_select(
            "billing_payments",
            filters={"confirmation_status": "eq.por_confirmar"},
            select="id,folio,customer_name,amount,payment_method,destination_money_account_id,payment_date,created_at",
            limit=200,
            order="payment_date.asc",
        )
        por_confirmar = por_confirmar_r.get("data") or [] if por_confirmar_r.get("ok") else []
        for p in por_confirmar:
            if p.get("payment_date"):
                p["dias_esperando"] = (date.today() - date.fromisoformat(p["payment_date"])).days

        # Cortes abiertos
        cortes_r = billing_db.rest_select("billing_cash_cuts", filters={"status": "eq.abierto"}, select="*", limit=50, order="cut_date.asc")
        cortes_abiertos = cortes_r.get("data") or [] if cortes_r.get("ok") else []

        # Totales
        total_ventas_dia = sum(money(r.get("total")) for r in remisiones_hoy)
        total_cobrado_dia = sum(money(r.get("paid_total")) for r in remisiones_hoy)
        cxc_dia = sum(money(r.get("balance_total") if r.get("balance_total") is not None else r.get("total")) for r in remisiones_hoy if r.get("status") not in ("cancelada", "pagada"))
        total_pagos_hoy = sum(money(p.get("amount")) for p in pagos_hoy)
        total_cxc_ant = sum(money(r.get("balance_total") if r.get("balance_total") is not None else r.get("total")) for r in cxc_anteriores)

        # Totales por cuenta (pagos de hoy)
        by_account: dict = {}
        for p in pagos_hoy:
            acc_id = str(p.get("destination_money_account_id") or "sin_cuenta")
            by_account[acc_id] = by_account.get(acc_id, 0) + money(p.get("amount"))

        return {
            "ok": True,
            "data": {
                "cut_date": cut_date,
                "ventas_dia": remisiones_hoy,
                "pagos_hoy": pagos_hoy,
                "cxc_anteriores": cxc_anteriores,
                "por_confirmar": por_confirmar,
                "cortes_abiertos": cortes_abiertos,
                "totales": {
                    "total_ventas_dia": total_ventas_dia,
                    "total_cobrado_dia": total_cobrado_dia,
                    "cxc_dia": cxc_dia,
                    "total_pagos_hoy": total_pagos_hoy,
                    "total_cxc_anteriores": total_cxc_ant,
                    "total_por_confirmar": sum(money(p.get("amount")) for p in por_confirmar),
                    "por_cuenta": by_account,
                },
            },
        }
