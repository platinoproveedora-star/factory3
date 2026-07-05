from __future__ import annotations

from datetime import datetime
from pathlib import Path

from factory.engine import SupabaseClient

_SCHEMA = "fleet4all"
_OUT_DIR = Path("/tmp/fleet4all_receipts")

_LABELS = {
    "es": {"title": "Recibo de liquidacion", "trips": "Viajes", "advances": "Anticipos", "net": "Neto a pagar"},
    "en": {"title": "Settlement receipt", "trips": "Trips", "advances": "Advances", "net": "Net pay"},
}


class ReceiptGenerateService:
    def ejecutar(self, context: dict) -> dict:
        empresa_id = str(context.get("empresa_id") or "").strip()
        settlement_folio = str(context.get("settlement_folio") or "").strip()
        if not empresa_id:
            return {"ok": False, "error": "empresa_id_requerido"}
        if not settlement_folio:
            return {"ok": False, "error": "missing_required_fields"}

        lang = str(context.get("language") or "es").strip().lower()
        if lang not in _LABELS:
            lang = "es"

        db = SupabaseClient({**context, "schema": _SCHEMA})

        settlement_res = db.rest_select(
            "settlements",
            filters={"empresa_id": f"eq.{empresa_id}", "settlement_folio": f"eq.{settlement_folio}"},
            select="*",
            limit=1,
        )
        if not settlement_res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": settlement_res.get("error")}}
        settlements = settlement_res.get("data") or []
        if not settlements:
            return {"ok": False, "error": "settlement_not_found"}
        settlement = settlements[0]

        trip_folios = settlement.get("trips_included") or []
        trips = []
        if trip_folios:
            trips_res = db.rest_select(
                "trips",
                filters={"empresa_id": f"eq.{empresa_id}", "trip_folio": f"in.({','.join(trip_folios)})"},
                select="trip_folio,origin,destination,trip_profit",
            )
            if not trips_res.get("ok"):
                return {"ok": False, "error": "db_persistence_failed", "data": {"detail": trips_res.get("error")}}
            trips = trips_res.get("data") or []

        advances_res = db.rest_select(
            "driver_advances",
            filters={"empresa_id": f"eq.{empresa_id}", "settled_in": f"eq.{settlement_folio}"},
            select="advance_folio,amount,concept,advance_date",
        )
        if not advances_res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": advances_res.get("error")}}
        advances = advances_res.get("data") or []

        receipt = {
            "empresa_id": empresa_id,
            "driver_key": settlement.get("driver_key"),
            "settlement_folio": settlement_folio,
            "period": {"from": settlement.get("period_from"), "to": settlement.get("period_to")},
            "trips": trips,
            "advances": advances,
            "gross_amount": settlement.get("gross_amount"),
            "advances_deducted": settlement.get("advances_deducted"),
            "other_deductions": settlement.get("other_deductions"),
            "net_amount": settlement.get("net_amount"),
            "currency": settlement.get("currency"),
            "status": settlement.get("status"),
            "pdf_path": None,
        }

        if context.get("dry_run", True):
            return {"ok": True, "data": {"receipt": receipt, "warnings": []}}

        path_result = self._write_file(receipt, lang)
        if not path_result.get("ok"):
            return {"ok": False, "error": "file_write_failed", "data": {"detail": path_result.get("error")}}
        receipt["pdf_path"] = path_result["path"]

        db.rest_update(
            "settlements", values={"receipt_pdf_path": receipt["pdf_path"]},
            filters={"empresa_id": f"eq.{empresa_id}", "settlement_folio": f"eq.{settlement_folio}"},
        )

        return {"ok": True, "data": {"receipt": receipt, "warnings": []}}

    def _write_file(self, receipt: dict, lang: str) -> dict:
        labels = _LABELS[lang]
        try:
            _OUT_DIR.mkdir(parents=True, exist_ok=True)
            ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            safe_driver = "".join(c if c.isalnum() else "_" for c in str(receipt.get("driver_key") or "driver"))
            try:
                from reportlab.pdfgen import canvas  # type: ignore

                path = _OUT_DIR / f"{receipt['empresa_id']}_{safe_driver}_{ts}.pdf"
                c = canvas.Canvas(str(path))
                y = 800
                c.drawString(40, y, f"{labels['title']} - {receipt['settlement_folio']}")
                y -= 24
                c.drawString(40, y, labels["trips"])
                y -= 16
                for trip in receipt["trips"]:
                    c.drawString(50, y, f"{trip.get('trip_folio')}  {trip.get('origin')} -> {trip.get('destination')}  profit={trip.get('trip_profit')}")
                    y -= 14
                y -= 10
                c.drawString(40, y, labels["advances"])
                y -= 16
                for adv in receipt["advances"]:
                    c.drawString(50, y, f"{adv.get('advance_folio')}  {adv.get('concept')}  {adv.get('amount')}")
                    y -= 14
                y -= 10
                c.drawString(40, y, f"{labels['net']}: {receipt['net_amount']} {receipt['currency']}")
                c.save()
            except ImportError:
                path = _OUT_DIR / f"{receipt['empresa_id']}_{safe_driver}_{ts}.html"
                trip_rows = "".join(
                    f"<tr><td>{t.get('trip_folio')}</td><td>{t.get('origin')}</td><td>{t.get('destination')}</td><td>{t.get('trip_profit')}</td></tr>"
                    for t in receipt["trips"]
                )
                adv_rows = "".join(
                    f"<tr><td>{a.get('advance_folio')}</td><td>{a.get('concept')}</td><td>{a.get('amount')}</td></tr>"
                    for a in receipt["advances"]
                )
                html = (
                    f"<h1>{labels['title']} - {receipt['settlement_folio']}</h1>"
                    f"<h3>{labels['trips']}</h3><table border=1><tr><th>Folio</th><th>Origen</th><th>Destino</th><th>Profit</th></tr>{trip_rows}</table>"
                    f"<h3>{labels['advances']}</h3><table border=1><tr><th>Folio</th><th>Concepto</th><th>Monto</th></tr>{adv_rows}</table>"
                    f"<p>{labels['net']}: {receipt['net_amount']} {receipt['currency']}</p>"
                )
                path.write_text(html, encoding="utf-8")
            return {"ok": True, "path": str(path)}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
