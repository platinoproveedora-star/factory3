from __future__ import annotations
import importlib.util
from collections import defaultdict
from datetime import date
from pathlib import Path


_COMMON_PATH = Path(__file__).resolve().parents[1] / "_common.py"
_COMMON_SPEC = importlib.util.spec_from_file_location("vertical_erp_billing_common", _COMMON_PATH)
if _COMMON_SPEC is None or _COMMON_SPEC.loader is None:
    raise ImportError("no se pudo cargar vertical_erp_billing/_common.py")
_COMMON = importlib.util.module_from_spec(_COMMON_SPEC)
_COMMON_SPEC.loader.exec_module(_COMMON)

SupabaseClient = _COMMON.SupabaseClient
money = _COMMON.money
resolve_billing_context = _COMMON.resolve_billing_context
sales_context = _COMMON.sales_context


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

        # Todos los documentos de ventas (base de clientes + montos)
        all_docs: list = []
        sales_ctx_result = sales_context(ctx)
        if sales_ctx_result.get("ok"):
            sales_ctx = sales_ctx_result["data"]
            rem_r = SupabaseClient(sales_ctx).rest_select(
                "sales_documents",
                filters={},
                select="customer_name_snapshot,document_date,total,document_type,status",
                limit=5000,
                order="document_date.desc",
            )
            all_docs = rem_r.get("data") or [] if rem_r.get("ok") else []

        today = date.today()
        m0 = _month_key(0)
        m1 = _month_key(1)
        m2 = _month_key(2)
        followups_by_key = self._load_followups(ctx)

        # Construir datos por cliente desde remisiones
        client_info: dict = {}       # key -> {name, last_purchase}
        client_monthly: dict = defaultdict(lambda: defaultdict(float))   # key -> {month: total}
        client_all_totals: dict = defaultdict(list)   # key -> [total, ...]

        for doc in all_docs:
            if (doc.get("document_type") or "remision") == "pedido":
                continue
            if doc.get("status") == "cancelada":
                continue
            name = (doc.get("customer_name_snapshot") or "").strip()
            key = name.lower()
            if not key:
                continue

            # Info básica
            if key not in client_info:
                client_info[key] = {"name": name, "last_purchase": None}
            d = doc.get("document_date") or ""
            if d and (client_info[key]["last_purchase"] is None or d > client_info[key]["last_purchase"]):
                client_info[key]["last_purchase"] = d

            # Montos por mes (ventas, no cobros)
            if d and len(d) >= 7:
                client_monthly[key][d[:7]] += money(doc.get("total"))

            # Histórico completo para ticket promedio
            t = money(doc.get("total"))
            if t > 0:
                client_all_totals[key].append(t)

        rows = []
        for key, info in client_info.items():
            by_month = client_monthly[key]
            all_amounts = client_all_totals[key]

            m_actual_v = round(by_month.get(m0, 0), 2)
            m1_v = round(by_month.get(m1, 0), 2)
            m2_v = round(by_month.get(m2, 0), 2)

            ticket_prom = round(sum(all_amounts) / len(all_amounts), 2) if all_amounts else 0

            ultima_compra = info["last_purchase"]
            dias_sin_comprar = (today - date.fromisoformat(ultima_compra)).days if ultima_compra else None

            semaforo = "verde"
            if dias_sin_comprar is not None:
                if dias_sin_comprar >= 13:
                    semaforo = "rojo"
                elif dias_sin_comprar >= 8:
                    semaforo = "amarillo"

            followup = followups_by_key.get(key) or {}
            rows.append({
                "customer_key": key,
                "customer_name": info["name"],
                "semaforo": semaforo,
                "ultima_compra": ultima_compra,
                "dias_sin_comprar": dias_sin_comprar,
                "ticket_promedio": ticket_prom,
                "m_actual": m_actual_v,
                "m1": m1_v,
                "m2": m2_v,
                "comments": followup.get("comments"),
                "last_call_date": followup.get("last_call_date"),
                "next_followup_date": followup.get("next_followup_date"),
                "offer_prices": followup.get("offer_prices"),
                "phone": followup.get("phone"),
                "followup_status": followup.get("status"),
                "followup_updated_at": followup.get("updated_at"),
            })

        rows.sort(key=lambda x: (x["m_actual"] + x["m1"] + x["m2"]), reverse=True)

        def _sum(field: str) -> float:
            return round(sum(r[field] for r in rows), 2)

        t_m_actual = _sum("m_actual")
        t_m1 = _sum("m1")
        t_m2 = _sum("m2")
        tend_base = t_m2 or t_m1
        trend = round((t_m1 - tend_base) / tend_base * 100, 1) if tend_base else 0

        return {
            "ok": True,
            "data": {
                "clientes": rows,
                "total_clientes": len(rows),
                "meses": {"m_actual": m0, "m1": m1, "m2": m2},
                "totales": {
                    "m_actual": t_m_actual,
                    "m1": t_m1,
                    "m2": t_m2,
                    "promedio_mensual": round((t_m1 + t_m2) / 2, 2) if t_m1 or t_m2 else 0,
                    "proyeccion": round((t_m_actual + t_m1 + t_m2) / 3, 2) if rows else 0,
                    "tendencia_pct": trend,
                },
            },
        }

    def _load_followups(self, ctx: dict) -> dict:
        result = SupabaseClient(ctx).rest_select(
            "erp_client_followups",
            filters={
                "empresa_id": ctx.get("company_id") or ctx.get("empresa_id"),
                "project_code": ctx.get("project_code"),
                "module_code": ctx.get("module_code"),
            },
            select="customer_key,comments,last_call_date,next_followup_date,offer_prices,phone,status,updated_at",
            limit=5000,
        )
        if not result.get("ok"):
            return {}
        return {
            str(row.get("customer_key") or "").strip().lower(): row
            for row in result.get("data") or []
            if str(row.get("customer_key") or "").strip()
        }
