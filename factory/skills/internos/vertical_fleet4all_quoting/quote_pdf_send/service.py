from __future__ import annotations

from datetime import datetime
from pathlib import Path

from factory.engine import SupabaseClient

_SCHEMA = "fleet4all"
_OUT_DIR = Path("/tmp/fleet4all_quotes")

_LABELS = {
    "es": {"title": "Cotizacion", "route": "Ruta", "price": "Precio", "valid": "Vigencia", "terms": "Condiciones: precio sujeto a disponibilidad de unidad."},
    "en": {"title": "Quote", "route": "Route", "price": "Price", "valid": "Valid until", "terms": "Terms: price subject to unit availability."},
}


def _runner():
    from factory.engine import SkillLoader, SkillRunner

    root = Path(__file__).resolve().parents[2]
    return SkillRunner(SkillLoader(internal_root=root))


class QuotePdfSendService:
    def ejecutar(self, context: dict) -> dict:
        empresa_id = str(context.get("empresa_id") or "").strip()
        quote_folio = str(context.get("quote_folio") or "").strip()
        if not empresa_id:
            return {"ok": False, "error": "empresa_id_requerido"}
        if not quote_folio:
            return {"ok": False, "error": "missing_required_fields"}

        lang = str(context.get("language") or "es").strip().lower()
        if lang not in _LABELS:
            lang = "es"
        company_profile = context.get("company_profile") if isinstance(context.get("company_profile"), dict) else {}

        db = SupabaseClient({**context, "schema": _SCHEMA})
        quote_res = db.rest_select("quotes", filters={"empresa_id": f"eq.{empresa_id}", "quote_folio": f"eq.{quote_folio}"}, select="*", limit=1)
        if not quote_res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": quote_res.get("error")}}
        quotes = quote_res.get("data") or []
        if not quotes:
            return {"ok": False, "error": "quote_not_found"}
        quote = quotes[0]

        document = {
            "empresa_id": empresa_id,
            "quote_folio": quote_folio,
            "company_profile": company_profile,
            "customer": quote.get("customer"),
            "origin": quote.get("origin"),
            "destination": quote.get("destination"),
            "cargo_type": quote.get("cargo_type"),
            "quoted_price": quote.get("quoted_price"),
            "currency": quote.get("currency"),
            "valid_until": quote.get("valid_until"),
            "status": quote.get("status"),
            "pdf_path": None,
        }

        dry_run = context.get("dry_run", True)
        if dry_run:
            return {"ok": True, "data": {"document": document, "warnings": []}}

        path_result = self._write_file(document, lang)
        if not path_result.get("ok"):
            return {"ok": False, "error": "file_write_failed", "data": {"detail": path_result.get("error")}}
        document["pdf_path"] = path_result["path"]
        db.rest_update("quotes", values={"pdf_path": document["pdf_path"]}, filters={"empresa_id": f"eq.{empresa_id}", "quote_folio": f"eq.{quote_folio}"})

        warnings: list[str] = []
        send_channel = context.get("send_channel")
        if send_channel:
            send_res = _runner().run(send_channel, {"to": quote.get("customer"), "message": f"{_LABELS[lang]['title']} {quote_folio}", "attachment_path": document["pdf_path"]})
            if not send_res.get("ok"):
                warnings.append(f"send_failed: {send_res.get('error')}")

        return {"ok": True, "data": {"document": document, "warnings": warnings}}

    def _write_file(self, document: dict, lang: str) -> dict:
        labels = _LABELS[lang]
        try:
            _OUT_DIR.mkdir(parents=True, exist_ok=True)
            ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            safe_customer = "".join(c if c.isalnum() else "_" for c in str(document.get("customer") or "cliente"))
            company_name = document.get("company_profile", {}).get("name", "")
            try:
                from reportlab.pdfgen import canvas  # type: ignore

                path = _OUT_DIR / f"{document['empresa_id']}_{safe_customer}_{ts}.pdf"
                c = canvas.Canvas(str(path))
                y = 800
                if company_name:
                    c.drawString(40, y, company_name)
                    y -= 20
                c.drawString(40, y, f"{labels['title']} {document['quote_folio']}")
                y -= 24
                c.drawString(40, y, f"{labels['route']}: {document['origin']} -> {document['destination']}")
                y -= 16
                c.drawString(40, y, f"{labels['price']}: {document['quoted_price']} {document['currency']}")
                y -= 16
                c.drawString(40, y, f"{labels['valid']}: {document['valid_until']}")
                y -= 24
                c.drawString(40, y, labels["terms"])
                c.save()
            except ImportError:
                path = _OUT_DIR / f"{document['empresa_id']}_{safe_customer}_{ts}.html"
                html = (
                    f"<h2>{company_name}</h2>" if company_name else ""
                ) + (
                    f"<h1>{labels['title']} {document['quote_folio']}</h1>"
                    f"<p>{labels['route']}: {document['origin']} -> {document['destination']}</p>"
                    f"<p>{labels['price']}: {document['quoted_price']} {document['currency']}</p>"
                    f"<p>{labels['valid']}: {document['valid_until']}</p>"
                    f"<p>{labels['terms']}</p>"
                )
                path.write_text(html, encoding="utf-8")
            return {"ok": True, "path": str(path)}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
