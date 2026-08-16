from __future__ import annotations

from factory.engine import SupabaseClient

_SCHEMA = "factu4all"
_FIELDS = "*"


class ExpenseVaultReportService:
    def ejecutar(self, context: dict) -> dict:
        company_id = str(context.get("company_id") or "").strip()
        if not company_id:
            return {"ok": False, "error": "company_id_requerido"}

        year = self._int(context.get("year"))
        month = self._int(context.get("month"))
        group_filter = str(context.get("classification_group") or "").strip()

        db = SupabaseClient({**context, "schema": _SCHEMA})
        res = db.rest_select(
            "cfdi_documents",
            filters={"company_id": f"eq.{company_id}", "direction": "eq.received"},
            select=_FIELDS,
            order="issued_at.desc",
            limit=5000,
        )
        if not res.get("ok"):
            return {"ok": False, "error": "db_query_failed", "data": {"detail": res.get("error")}}

        documents = []
        for doc in res.get("data") or []:
            issued_at = doc.get("issued_at") or ""
            doc_year, doc_month = self._year_month(issued_at)
            if year and doc_year != year:
                continue
            if month and doc_month != month:
                continue
            if group_filter and doc.get("classification_group") != group_filter:
                continue
            documents.append(doc)

        groups: dict[str, dict] = {}
        periods: dict[str, dict] = {}
        for doc in documents:
            group = doc.get("classification_group") or "pending_review"
            g = groups.setdefault(group, {"classification_group": group, "count": 0, "subtotal": 0.0, "tax_total": 0.0, "retencion_iva": 0.0, "retencion_isr": 0.0, "total": 0.0})
            g["count"] += 1
            g["subtotal"] += float(doc.get("subtotal") or 0)
            g["tax_total"] += float(doc.get("tax_total") or 0)
            g["retencion_iva"] += float(doc.get("retencion_iva") or 0)
            g["retencion_isr"] += float(doc.get("retencion_isr") or 0)
            g["total"] += float(doc.get("total") or 0)

            doc_year, doc_month = self._year_month(doc.get("issued_at") or "")
            period_key = f"{doc_year:04d}-{doc_month:02d}" if doc_year and doc_month else "sin_fecha"
            p = periods.setdefault(period_key, {"period": period_key, "count": 0, "total": 0.0})
            p["count"] += 1
            p["total"] += float(doc.get("total") or 0)

        for g in groups.values():
            for key in ("subtotal", "tax_total", "retencion_iva", "retencion_isr", "total"):
                g[key] = round(g[key], 2)
        for p in periods.values():
            p["total"] = round(p["total"], 2)

        pending_review_count = groups.get("pending_review", {}).get("count", 0)
        pending_rep_count = sum(1 for d in documents if d.get("payment_status") == "pending_rep")

        return {
            "ok": True,
            "data": {
                "documents": documents,
                "groups": sorted(groups.values(), key=lambda g: -g["total"]),
                "periods": sorted(periods.values(), key=lambda p: p["period"]),
                "pending_review_count": pending_review_count,
                "pending_rep_count": pending_rep_count,
                "total_documents": len(documents),
            },
        }

    def _int(self, value) -> int:
        try:
            return int(value) if value not in (None, "") else 0
        except (TypeError, ValueError):
            return 0

    def _year_month(self, issued_at: str) -> tuple[int, int]:
        try:
            return int(issued_at[0:4]), int(issued_at[5:7])
        except (ValueError, IndexError):
            return 0, 0
