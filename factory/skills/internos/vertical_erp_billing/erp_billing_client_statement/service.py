from __future__ import annotations
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import SupabaseClient, blank, money, resolve_billing_context, sales_context  # noqa: E402


class ErpBillingClientStatementService:
    def ejecutar(self, context: dict) -> dict:
        ctx_result = resolve_billing_context(context)
        if not ctx_result.get("ok"):
            return ctx_result
        ctx = ctx_result["data"]

        customer_name = blank(context.get("customer_name"))
        customer_id = blank(context.get("customer_id"))
        if not customer_name and not customer_id:
            return {"ok": False, "error": "customer_name o customer_id requerido"}

        date_from = blank(context.get("date_from"))
        date_to = blank(context.get("date_to"))

        billing_db = SupabaseClient(ctx)
        pay_filters: dict = {}
        ant_filters: dict = {}
        if customer_id:
            pay_filters["customer_id"] = f"eq.{customer_id}"
            ant_filters["customer_id"] = f"eq.{customer_id}"
        elif customer_name:
            pay_filters["customer_name"] = f"ilike.%{customer_name}%"
            ant_filters["customer_name"] = f"ilike.%{customer_name}%"
        if date_from:
            pay_filters["payment_date"] = f"gte.{date_from}"
        if date_to:
            pay_filters["payment_date"] = f"lte.{date_to}"

        payments_r = billing_db.rest_select("billing_payments", filters=pay_filters, select="id,folio,payment_date,amount,unapplied_amount,payment_method,status,confirmation_status,customer_name", limit=500, order="payment_date.asc")
        anticipos_r = billing_db.rest_select("billing_anticipos", filters=ant_filters, select="id,folio,payment_date,amount,unapplied_amount,status,customer_name", limit=200, order="payment_date.asc")

        payments = payments_r.get("data") or [] if payments_r.get("ok") else []
        anticipos = anticipos_r.get("data") or [] if anticipos_r.get("ok") else []
        anticipos_disp = [a for a in anticipos if a.get("status") in ("disponible", "parcial")]

        # Remisiones del cliente desde ventas
        remisiones = []
        sales_ctx_result = sales_context(ctx)
        if sales_ctx_result.get("ok"):
            sales_ctx = sales_ctx_result["data"]
            rem_filters: dict = {}
            if customer_id:
                rem_filters["customer_id"] = f"eq.{customer_id}"
            elif customer_name:
                rem_filters["customer_name_snapshot"] = f"ilike.%{customer_name}%"
            if date_from:
                rem_filters["document_date"] = f"gte.{date_from}"
            if date_to:
                rem_filters["document_date"] = f"lte.{date_to}"
            rem_r = SupabaseClient(sales_ctx).rest_select("sales_documents", filters=rem_filters, select="id,folio,document_date,total,paid_total,balance_total,status,customer_name_snapshot", limit=500, order="document_date.asc")
            remisiones = rem_r.get("data") or [] if rem_r.get("ok") else []

        # Kardex cronologico
        kardex = []
        saldo_acum = 0.0
        events = []
        for r in remisiones:
            events.append(("remision", r.get("document_date") or "", r))
        for p in payments:
            events.append(("pago", p.get("payment_date") or "", p))
        for a in anticipos:
            events.append(("anticipo", a.get("payment_date") or "", a))
        events.sort(key=lambda x: x[1])

        for kind, evt_date, row in events:
            if kind == "remision":
                cargo = money(row.get("total"))
                saldo_acum = round(saldo_acum + cargo, 2)
                kardex.append({"fecha": evt_date, "tipo": "Remisión", "folio": row.get("folio"), "concepto": f"Venta {row.get('folio')}", "cargo": cargo, "abono": 0, "saldo": saldo_acum, "status": row.get("status")})
            elif kind == "pago":
                abono = money(row.get("amount"))
                saldo_acum = round(saldo_acum - abono, 2)
                kardex.append({"fecha": evt_date, "tipo": "Pago", "folio": row.get("folio"), "concepto": f"Pago {row.get('payment_method', '')}", "cargo": 0, "abono": abono, "saldo": saldo_acum, "status": row.get("confirmation_status")})
            elif kind == "anticipo":
                abono = money(row.get("amount"))
                saldo_acum = round(saldo_acum - abono, 2)
                kardex.append({"fecha": evt_date, "tipo": "Anticipo", "folio": row.get("folio"), "concepto": "Anticipo de cliente", "cargo": 0, "abono": abono, "saldo": saldo_acum, "status": row.get("status")})

        # KPIs
        total_facturado = sum(money(r.get("total")) for r in remisiones)
        total_cobrado = sum(money(r.get("paid_total")) for r in remisiones)
        saldo_pendiente = sum(money(r.get("balance_total") if r.get("balance_total") is not None else r.get("total")) for r in remisiones if r.get("status") not in ("cancelada", "pagada"))
        anticipos_total = sum(money(a.get("unapplied_amount")) for a in anticipos_disp)
        vencidas = sum(1 for r in remisiones if r.get("status") not in ("cancelada", "pagada") and money(r.get("balance_total") if r.get("balance_total") is not None else r.get("total")) > 0)

        today = date.today()
        pagos_fechas = [p.get("payment_date") for p in payments if p.get("payment_date")]
        ultimo_pago = max(pagos_fechas) if pagos_fechas else None
        dias_sin_pagar = (today - date.fromisoformat(ultimo_pago)).days if ultimo_pago else None
        montos = [money(p.get("amount")) for p in payments if money(p.get("amount")) > 0]
        ticket_promedio = round(sum(montos) / len(montos), 2) if montos else 0
        meses = {}
        for p in payments:
            if p.get("payment_date"):
                mes = p["payment_date"][:7]
                meses[mes] = meses.get(mes, 0) + money(p.get("amount"))
        pago_promedio_mes = round(sum(meses.values()) / len(meses), 2) if meses else 0

        # Frecuencia de compra
        rem_fechas = sorted([r.get("document_date") for r in remisiones if r.get("document_date")])
        frecuencia_dias = None
        if len(rem_fechas) >= 2:
            diffs = [(date.fromisoformat(rem_fechas[i+1]) - date.fromisoformat(rem_fechas[i])).days for i in range(len(rem_fechas)-1)]
            frecuencia_dias = round(sum(diffs) / len(diffs))

        ultima_compra = max(rem_fechas) if rem_fechas else None
        dias_sin_comprar = (today - date.fromisoformat(ultima_compra)).days if ultima_compra else None

        return {
            "ok": True,
            "data": {
                "customer_name": customer_name or (remisiones[0].get("customer_name_snapshot") if remisiones else ""),
                "kpis": {
                    "total_facturado": total_facturado,
                    "total_cobrado": total_cobrado,
                    "saldo_pendiente": saldo_pendiente,
                    "anticipos_disponibles": anticipos_total,
                    "remisiones_vencidas": vencidas,
                    "ultimo_pago": ultimo_pago,
                    "dias_sin_pagar": dias_sin_pagar,
                    "ultima_compra": ultima_compra,
                    "dias_sin_comprar": dias_sin_comprar,
                    "ticket_promedio": ticket_promedio,
                    "pago_promedio_mes": pago_promedio_mes,
                    "frecuencia_compra_dias": frecuencia_dias,
                },
                "remisiones": remisiones,
                "payments": payments,
                "anticipos_disponibles": anticipos_disp,
                "kardex": kardex,
            },
        }
