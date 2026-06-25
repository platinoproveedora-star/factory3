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
        account_map = self._account_map(context, ctx)

        # Pagos recibidos HOY
        pagos_hoy_r = billing_db.rest_select(
            "billing_payments",
            filters={"payment_date": f"eq.{cut_date}"},
            select="id,folio,customer_name,amount,payment_method,destination_money_account_id,confirmation_status,status",
            limit=500,
        )
        pagos_hoy = pagos_hoy_r.get("data") or [] if pagos_hoy_r.get("ok") else []
        for pago in pagos_hoy:
            account = account_map.get(str(pago.get("destination_money_account_id") or ""))
            pago["destination_account_name"] = account.get("account_name") if account else "Sin cuenta"
            pago["destination_account_folio"] = account.get("folio") if account else None
            pago["destination_account_type"] = account.get("account_type") if account else None

        # Documentos comerciales del dia, separados por tipo.
        pedidos_hoy = []
        remisiones_hoy = []
        sales_ctx_result = sales_context(ctx)
        if sales_ctx_result.get("ok"):
            sales_ctx = sales_ctx_result["data"]
            ped_r = SupabaseClient(sales_ctx).rest_select(
                "sales_documents",
                filters={"document_date": f"eq.{cut_date}", "document_type": "eq.pedido"},
                select="id,folio,document_type,document_date,customer_name_snapshot,total,paid_total,balance_total,status",
                limit=500,
            )
            pedidos_hoy = ped_r.get("data") or [] if ped_r.get("ok") else []
            rem_r = SupabaseClient(sales_ctx).rest_select(
                "sales_documents",
                filters={"document_date": f"eq.{cut_date}", "document_type": "eq.remision"},
                select="id,folio,document_type,document_date,customer_name_snapshot,total,paid_total,balance_total,status",
                limit=500,
            )
            remisiones_hoy = rem_r.get("data") or [] if rem_r.get("ok") else []

        # CXC pendientes de fechas anteriores
        cxc_r = SupabaseClient(sales_ctx).rest_select(
            "sales_documents",
            filters={"status": "neq.cancelada", "document_type": "eq.remision"},
            select="id,folio,document_type,document_date,customer_name_snapshot,total,paid_total,balance_total,status",
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

        payment_accounts_by_folio = self._payment_accounts_by_sales_folio(billing_db, remisiones_hoy, account_map)
        for remision in remisiones_hoy:
            remision["payment_accounts"] = payment_accounts_by_folio.get(str(remision.get("folio") or ""), [])
            remision["payment_account_names"] = ", ".join(row["account_name"] for row in remision["payment_accounts"]) or "Sin cobro"

        gastos_dia = self._expenses(context, ctx, cut_date)

        # Totales
        total_pedidos_dia = sum(money(r.get("total")) for r in pedidos_hoy)
        total_remisiones_dia = sum(money(r.get("total")) for r in remisiones_hoy)
        total_cobrado_dia = sum(money(r.get("paid_total")) for r in remisiones_hoy)
        cxc_dia = sum(money(r.get("balance_total") if r.get("balance_total") is not None else r.get("total")) for r in remisiones_hoy if r.get("status") not in ("cancelada", "pagada"))
        total_pagos_hoy = sum(money(p.get("amount")) for p in pagos_hoy)
        total_cxc_ant = sum(money(r.get("balance_total") if r.get("balance_total") is not None else r.get("total")) for r in cxc_anteriores)
        total_gastos_dia = sum(money(g.get("monto")) for g in gastos_dia)

        # Totales por cuenta (pagos de hoy)
        by_account: dict = {}
        ingresos_por_cuenta: dict = {}
        ingresos_por_metodo: dict = {}
        for p in pagos_hoy:
            acc_id = str(p.get("destination_money_account_id") or "sin_cuenta")
            amount = money(p.get("amount"))
            by_account[acc_id] = by_account.get(acc_id, 0) + amount
            account_name = p.get("destination_account_name") or "Sin cuenta"
            ingresos_por_cuenta[account_name] = round(ingresos_por_cuenta.get(account_name, 0) + amount, 2)
            method = str(p.get("payment_method") or "otro").lower()
            ingresos_por_metodo[method] = round(ingresos_por_metodo.get(method, 0) + amount, 2)

        egresos_por_cuenta: dict = {}
        egresos_por_tipo: dict = {"efectivo": 0.0, "tc": 0.0, "otros": 0.0}
        for gasto in gastos_dia:
            amount = money(gasto.get("monto"))
            account_name = gasto.get("cta_retiro_nombre") or "Sin cuenta"
            egresos_por_cuenta[account_name] = round(egresos_por_cuenta.get(account_name, 0) + amount, 2)
            account_type = str(gasto.get("cta_retiro_tipo") or "").lower()
            account_text = f"{account_name} {gasto.get('cta_retiro_folio') or ''}".lower()
            if account_type == "cash" or "efectivo" in account_text:
                egresos_por_tipo["efectivo"] = round(egresos_por_tipo["efectivo"] + amount, 2)
            elif account_type in {"credit_card", "tc"} or "tc " in account_text or "tarjeta" in account_text:
                egresos_por_tipo["tc"] = round(egresos_por_tipo["tc"] + amount, 2)
            else:
                egresos_por_tipo["otros"] = round(egresos_por_tipo["otros"] + amount, 2)

        total_efectivo_cobrado = sum(amount for method, amount in ingresos_por_metodo.items() if method in {"cash", "efectivo"})
        total_transferencias_cobradas = sum(amount for method, amount in ingresos_por_metodo.items() if method in {"transfer", "transferencia", "deposito"})

        return {
            "ok": True,
            "data": {
                "cut_date": cut_date,
                "pedidos_dia": pedidos_hoy,
                "remisiones_dia": remisiones_hoy,
                "ventas_dia": remisiones_hoy,
                "pagos_hoy": pagos_hoy,
                "gastos_dia": gastos_dia,
                "cxc_anteriores": cxc_anteriores,
                "por_confirmar": por_confirmar,
                "cortes_abiertos": cortes_abiertos,
                "totales": {
                    "total_pedidos_dia": total_pedidos_dia,
                    "total_remisiones_dia": total_remisiones_dia,
                    "total_ventas_dia": total_remisiones_dia,
                    "total_cobrado_dia": total_cobrado_dia,
                    "cxc_dia": cxc_dia,
                    "total_pagos_hoy": total_pagos_hoy,
                    "total_gastos_dia": total_gastos_dia,
                    "gastos_efectivo": egresos_por_tipo["efectivo"],
                    "gastos_tc": egresos_por_tipo["tc"],
                    "gastos_otros": egresos_por_tipo["otros"],
                    "total_efectivo_cobrado": round(total_efectivo_cobrado, 2),
                    "total_transferencias_cobradas": round(total_transferencias_cobradas, 2),
                    "total_cxc_anteriores": total_cxc_ant,
                    "total_por_confirmar": sum(money(p.get("amount")) for p in por_confirmar),
                    "por_cuenta": by_account,
                    "ingresos_por_cuenta": ingresos_por_cuenta,
                    "egresos_por_cuenta": egresos_por_cuenta,
                    "ingresos_por_metodo": ingresos_por_metodo,
                    "egresos_por_tipo": egresos_por_tipo,
                },
            },
        }

    def _account_map(self, context: dict, ctx: dict) -> dict:
        schema = str(context.get("banks_schema") or ctx.get("banks_schema") or "").strip()
        if not schema:
            return {}
        result = SupabaseClient({**ctx, "schema": schema}).rest_select(
            "banks_accounts",
            filters={"empresa_id": ctx.get("company_id")},
            select="id,folio,account_name,account_type,status",
            limit=500,
        )
        rows = result.get("data") or [] if result.get("ok") else []
        return {str(row.get("id")): row for row in rows if row.get("id")}

    def _payment_accounts_by_sales_folio(self, billing_db: SupabaseClient, remisiones: list[dict], account_map: dict) -> dict:
        folios = [str(row.get("folio") or "").strip() for row in remisiones if row.get("folio")]
        if not folios:
            return {}
        apps_r = billing_db.rest_select(
            "billing_payment_applications",
            filters={"sales_folio": f"in.({','.join(folios)})", "status": "eq.aplicado"},
            select="payment_id,sales_folio,amount_applied",
            limit=1000,
        )
        apps = apps_r.get("data") or [] if apps_r.get("ok") else []
        payment_ids = [str(row.get("payment_id") or "") for row in apps if row.get("payment_id")]
        if not payment_ids:
            return {}
        payments_r = billing_db.rest_select(
            "billing_payments",
            filters={"id": f"in.({','.join(payment_ids)})"},
            select="id,destination_money_account_id,payment_method",
            limit=1000,
        )
        payments = {str(row.get("id")): row for row in (payments_r.get("data") or [] if payments_r.get("ok") else [])}
        by_folio: dict = {}
        for app in apps:
            payment = payments.get(str(app.get("payment_id") or "")) or {}
            account_id = str(payment.get("destination_money_account_id") or "")
            account = account_map.get(account_id) or {}
            name = account.get("account_name") or "Sin cuenta"
            by_folio.setdefault(str(app.get("sales_folio") or ""), {})
            bucket = by_folio[str(app.get("sales_folio") or "")]
            if name not in bucket:
                bucket[name] = {"account_name": name, "amount": 0.0, "payment_method": payment.get("payment_method")}
            bucket[name]["amount"] = round(bucket[name]["amount"] + money(app.get("amount_applied")), 2)
        return {folio: list(rows.values()) for folio, rows in by_folio.items()}

    def _expenses(self, context: dict, ctx: dict, cut_date: str) -> list[dict]:
        schema = str(context.get("expenses_schema") or context.get("expense_schema") or "").strip()
        if not schema:
            return []
        result = SupabaseClient({**ctx, "schema": schema}).rest_select(
            "gastos",
            filters={"fecha": f"eq.{cut_date}"},
            select="folio,fecha,monto,descripcion,cta_retiro_id,cta_retiro_folio,cta_retiro_nombre,categorias_gasto(nombre)",
            order="fecha.asc,folio.asc",
            limit=1000,
        )
        rows = result.get("data") or [] if result.get("ok") else []
        account_map = self._account_map(context, ctx)
        gastos = []
        for row in rows:
            account = account_map.get(str(row.get("cta_retiro_id") or ""))
            gastos.append({
                "folio": row.get("folio"),
                "fecha": row.get("fecha"),
                "monto": money(row.get("monto")),
                "descripcion": row.get("descripcion") or "",
                "categoria": (row.get("categorias_gasto") or {}).get("nombre") or "",
                "cta_retiro_id": row.get("cta_retiro_id"),
                "cta_retiro_folio": row.get("cta_retiro_folio"),
                "cta_retiro_nombre": row.get("cta_retiro_nombre") or (account or {}).get("account_name") or "Sin cuenta",
                "cta_retiro_tipo": (account or {}).get("account_type"),
            })
        return gastos
