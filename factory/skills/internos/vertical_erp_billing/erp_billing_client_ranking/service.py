from __future__ import annotations
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import SupabaseClient, money, resolve_billing_context, sales_context  # noqa: E402


def _month_key(offset: int) -> str:
    today = date.today()
    m = today.month - offset
    y = today.year
    while m <= 0:
        m += 12
        y -= 1
    return f"{y}-{m:02d}"


class ErpBillingClientRankingService:
    def ejecutar(self, context: dict) -> dict:
        ctx_result = resolve_billing_context(context)
        if not ctx_result.get("ok"):
            return ctx_result
        ctx = ctx_result["data"]

        billing_db = SupabaseClient(ctx)
        pay_r = billing_db.rest_select(
            "billing_payments",
            filters={},
            select="customer_name,customer_id,amount,payment_date,status",
            limit=2000,
            order="payment_date.desc",
        )
        payments = pay_r.get("data") or [] if pay_r.get("ok") else []

        # Base de clientes: TODOS los documentos de ventas (solo remisiones, no pedidos)
        all_docs: list = []
        sales_ctx_result = sales_context(ctx)
        if sales_ctx_result.get("ok"):
            sales_ctx = sales_ctx_result["data"]
            rem_r = SupabaseClient(sales_ctx).rest_select(
                "sales_documents",
                filters={},
                select="customer_name_snapshot,customer_id,document_date,total,document_type",
                limit=2000,
                order="document_date.desc",
            )
            all_docs = rem_r.get("data") or [] if rem_r.get("ok") else []

        today = date.today()
        m0 = _month_key(0)
        m1 = _month_key(1)
        m2 = _month_key(2)
        m3 = _month_key(3)

        # Índice de pagos por nombre de cliente (lowercase)
        payments_by_name: dict = defaultdict(list)
        for p in payments:
            key = (p.get("customer_name") or "").strip().lower()
            if key:
                payments_by_name[key].append(p)

        # Construir base desde remisiones (todos los clientes que han comprado)
        all_clients: dict = {}  # key -> {name, last_purchase}
        for doc in all_docs:
            if (doc.get("document_type") or "remision") == "pedido":
                continue  # pedidos no determinan cartera de clientes
            name = (doc.get("customer_name_snapshot") or "").strip()
            key = name.lower()
            if not key:
                continue
            if key not in all_clients:
                all_clients[key] = {"name": name, "last_purchase": None}
            d = doc.get("document_date")
            if d and (all_clients[key]["last_purchase"] is None or d > all_clients[key]["last_purchase"]):
                all_clients[key]["last_purchase"] = d

        rows = []
        for key, client_data in all_clients.items():
            pays = payments_by_name.get(key, [])
            by_month: dict = defaultdict(float)
            for p in pays:
                if p.get("payment_date") and len(p["payment_date"]) >= 7:
                    mk = p["payment_date"][:7]
                    by_month[mk] += money(p.get("amount"))

            amounts = [money(p.get("amount")) for p in pays if money(p.get("amount")) > 0]
            ticket_prom = round(sum(amounts) / len(amounts), 2) if amounts else 0
            months_vals = [v for v in by_month.values() if v > 0]
            pago_prom_mes = round(sum(months_vals) / len(months_vals), 2) if months_vals else 0
            pay_dates = sorted([p["payment_date"] for p in pays if p.get("payment_date")], reverse=True)
            ultimo_pago = pay_dates[0] if pay_dates else None
            dias_sin_pagar = (today - date.fromisoformat(ultimo_pago)).days if ultimo_pago else None
            ultima_compra = client_data["last_purchase"]
            dias_sin_comprar = (today - date.fromisoformat(ultima_compra)).days if ultima_compra else None

            semaforo = "verde"
            if dias_sin_comprar is not None:
                if dias_sin_comprar >= 21:
                    semaforo = "rojo"
                elif dias_sin_comprar >= 15:
                    semaforo = "amarillo"

            m_actual_v = round(by_month.get(m0, 0), 2)
            m1_v = round(by_month.get(m1, 0), 2)
            m2_v = round(by_month.get(m2, 0), 2)
            m3_v = round(by_month.get(m3, 0), 2)

            rows.append({
                "customer_key": key,
                "customer_name": client_data["name"],
                "semaforo": semaforo,
                "ultimo_pago": ultimo_pago,
                "dias_sin_pagar": dias_sin_pagar,
                "ultima_compra": ultima_compra,
                "dias_sin_comprar": dias_sin_comprar,
                "ticket_promedio": ticket_prom,
                "pago_promedio_mes": pago_prom_mes,
                "m_actual": m_actual_v,
                "m1": m1_v,
                "m2": m2_v,
                "m3": m3_v,
                "total_3m": round(m1_v + m2_v + m3_v, 2),
            })

        # Ordenar por actividad total descendente (incluye mes actual)
        rows.sort(key=lambda x: (x["m_actual"] + x["m1"] + x["m2"] + x["m3"]), reverse=True)

        def _sum(field: str) -> float:
            return round(sum(r[field] for r in rows), 2)

        t_m_actual = _sum("m_actual")
        t_m1, t_m2, t_m3 = _sum("m1"), _sum("m2"), _sum("m3")
        t_total = round(t_m_actual + t_m1 + t_m2, 2)
        avg_2m = round((t_m1 + t_m2) / 2, 2) if t_m1 or t_m2 else 0
        tend_base = t_m2 or t_m3
        trend = round((t_m1 - tend_base) / tend_base * 100, 1) if tend_base else 0

        return {
            "ok": True,
            "data": {
                "clientes": rows,
                "total_clientes": len(rows),
                "meses": {"m_actual": m0, "m1": m1, "m2": m2, "m3": m3},
                "totales": {
                    "m_actual": t_m_actual,
                    "m1": t_m1,
                    "m2": t_m2,
                    "m3": t_m3,
                    "total_3m": _sum("total_3m"),
                    "promedio_mensual": avg_2m,
                    "proyeccion": round((t_m_actual + t_m1 + t_m2) / 3, 2) if rows else 0,
                    "tendencia_pct": trend,
                },
            },
        }
