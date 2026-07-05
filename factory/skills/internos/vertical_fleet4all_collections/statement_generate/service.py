from __future__ import annotations

from datetime import datetime
from pathlib import Path

from factory.engine import SupabaseClient

_SCHEMA = "fleet4all"
_OUT_DIR = Path("/tmp/fleet4all_statements")


class StatementGenerateService:
    def ejecutar(self, context: dict) -> dict:
        empresa_id = str(context.get("empresa_id") or "").strip()
        customer = str(context.get("customer") or "").strip()
        if not empresa_id:
            return {"ok": False, "error": "empresa_id_requerido"}
        if not customer:
            return {"ok": False, "error": "missing_required_fields"}

        period = context.get("period") if isinstance(context.get("period"), dict) else {}
        period_from = period.get("from")
        period_to = period.get("to")

        db = SupabaseClient({**context, "schema": _SCHEMA})

        trips_res = db.rest_select(
            "trips",
            filters={"empresa_id": f"eq.{empresa_id}", "customer": f"eq.{customer}"},
            select="trip_folio,departure_date,sale_price,currency",
        )
        if not trips_res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": trips_res.get("error")}}
        all_trips = trips_res.get("data") or []
        if not all_trips:
            return {"ok": False, "error": "customer_not_found"}

        def in_period(value: str | None) -> bool:
            if not (period_from or period_to):
                return True
            if not value:
                return False
            if period_from and value < period_from:
                return False
            if period_to and value > period_to:
                return False
            return True

        scoped_trips = [t for t in all_trips if in_period(t.get("departure_date"))]

        payments_res = db.rest_select(
            "payments",
            filters={"empresa_id": f"eq.{empresa_id}", "trip_folio": f"in.({','.join(t['trip_folio'] for t in scoped_trips) or 'none'})"},
            select="trip_folio,amount",
        )
        if not payments_res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": payments_res.get("error")}}
        paid_by_trip: dict[str, float] = {}
        for p in payments_res.get("data") or []:
            key = p.get("trip_folio")
            paid_by_trip[key] = paid_by_trip.get(key, 0.0) + float(p.get("amount") or 0)

        lines = []
        total_balance = 0.0
        currency = "MXN"
        for t in scoped_trips:
            total = float(t.get("sale_price") or 0)
            paid = paid_by_trip.get(t.get("trip_folio"), 0.0)
            balance = max(0.0, total - paid)
            total_balance += balance
            currency = t.get("currency") or currency
            lines.append(
                {"trip_folio": t.get("trip_folio"), "trip_date": t.get("departure_date"),
                 "total": total, "paid": paid, "balance": round(balance, 2)}
            )

        statement = {
            "empresa_id": empresa_id,
            "customer": customer,
            "period": {"from": period_from, "to": period_to},
            "lines": lines,
            "total_balance": round(total_balance, 2),
            "currency": currency,
            "pdf_path": None,
        }

        dry_run = context.get("dry_run", True)
        if context.get("pdf") and not dry_run:
            path_result = self._write_file(statement)
            if not path_result.get("ok"):
                return {"ok": False, "error": "file_write_failed", "data": {"detail": path_result.get("error")}}
            statement["pdf_path"] = path_result["path"]

        return {"ok": True, "data": {"statement": statement, "warnings": []}}

    def _write_file(self, statement: dict) -> dict:
        try:
            _OUT_DIR.mkdir(parents=True, exist_ok=True)
            ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            safe_customer = "".join(c if c.isalnum() else "_" for c in statement["customer"])
            try:
                from reportlab.pdfgen import canvas  # type: ignore

                path = _OUT_DIR / f"{statement['empresa_id']}_{safe_customer}_{ts}.pdf"
                c = canvas.Canvas(str(path))
                y = 800
                c.drawString(40, y, f"Estado de cuenta - {statement['customer']}")
                y -= 20
                for line in statement["lines"]:
                    c.drawString(40, y, f"{line['trip_folio']}  {line['trip_date']}  total={line['total']} paid={line['paid']} balance={line['balance']}")
                    y -= 16
                c.drawString(40, y - 10, f"Total balance: {statement['total_balance']} {statement['currency']}")
                c.save()
            except ImportError:
                path = _OUT_DIR / f"{statement['empresa_id']}_{safe_customer}_{ts}.html"
                rows = "".join(
                    f"<tr><td>{l['trip_folio']}</td><td>{l['trip_date']}</td><td>{l['total']}</td>"
                    f"<td>{l['paid']}</td><td>{l['balance']}</td></tr>"
                    for l in statement["lines"]
                )
                html = (
                    f"<h1>Estado de cuenta - {statement['customer']}</h1>"
                    f"<table border=1><tr><th>Trip</th><th>Fecha</th><th>Total</th><th>Pagado</th><th>Saldo</th></tr>{rows}</table>"
                    f"<p>Total balance: {statement['total_balance']} {statement['currency']}</p>"
                )
                path.write_text(html, encoding="utf-8")
            return {"ok": True, "path": str(path)}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
