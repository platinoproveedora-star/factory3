from __future__ import annotations

from html import escape

from factory.engine import SupabaseClient


class ErpVentasFolioCobranzaPdfService:
    def ejecutar(self, context: dict) -> dict:
        doc = context.get("document") if isinstance(context.get("document"), dict) else None
        if doc is None:
            doc_id = str(context.get("id") or context.get("document_id") or "").strip()
            folio = str(context.get("folio") or "").strip()
            if not doc_id and not folio:
                return {"ok": False, "error": "id o folio requerido"}
            ctx = self._sales_context(context)
            if not ctx.get("ok"):
                return ctx
            filters = {"id": doc_id} if doc_id else {"folio": folio}
            result = SupabaseClient(ctx["data"]).rest_select(
                "sales_documents",
                filters=filters,
                select="id,folio,external_folio,customer_name_snapshot,status,document_date,total,balance_total,notes",
                limit=1,
            )
            if not result.get("ok"):
                return result
            rows = result.get("data") or []
            if not rows:
                return {"ok": False, "error": "documento no encontrado"}
            doc = rows[0]

        html = self.html(context, doc)
        return {
            "ok": True,
            "data": {
                "folio": self._receipt_folio(doc),
                "document_folio": doc.get("folio"),
                "filename": f"{self._receipt_folio(doc)}.html",
                "html": html,
            },
        }

    def html(self, context: dict, doc: dict) -> str:
        return self._document(context, doc, standalone=True)

    def fragment(self, context: dict, doc: dict) -> str:
        return self._document(context, doc, standalone=False)

    def _document(self, context: dict, doc: dict, standalone: bool) -> str:
        content = f"""
  <section class="receipt-page">
    <header>
      <div>
        <h1>{escape(self._brand(context))}</h1>
        <p class="muted">Folio de cobranza</p>
      </div>
      <div class="right">
        <h1>{escape(self._receipt_folio(doc))}</h1>
        <p class="muted">Fecha: ____________________</p>
      </div>
    </header>
    <section class="box">
      <div class="grid two">
        <p><strong>Cliente:</strong><br />{escape(str(doc.get('customer_name_snapshot') or ''))}</p>
        <p><strong>Documento:</strong><br />{escape(str(doc.get('folio') or ''))}</p>
        <p><strong>Folio externo:</strong><br />{escape(str(doc.get('external_folio') or '-'))}</p>
        <p><strong>Importe del documento:</strong><br />{self._money(doc.get('total'))}</p>
      </div>
    </section>
    <section class="totals">
      <div class="total"><span>Total documento</span><span>{self._money(doc.get('total'))}</span></div>
      <div><span>Saldo actual</span><span>{self._money(doc.get('balance_total'))}</span></div>
    </section>
    <section class="payment-boxes">
      <div class="pay-row"><span>Pago en efectivo</span><div class="write-box"></div></div>
      <div class="pay-row"><span>Pago transferencia</span><div class="write-box"></div></div>
      <div class="notes-box"><span>Notas</span></div>
    </section>
    <section class="signature">
      <div>
        <span>Nombre de quien recibe</span>
      </div>
      <div>
        <span>Firma de quien recibe</span>
      </div>
    </section>
  </section>
"""
        if not standalone:
            return content
        return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <title>{escape(self._receipt_folio(doc))}</title>
  <style>{self.styles()}</style>
</head>
<body>
  <button class="no-print" onclick="window.print()">Imprimir / guardar PDF</button>
{content}
</body>
</html>"""

    def styles(self) -> str:
        return """
    body { font-family: Arial, sans-serif; color: #111827; margin: 32px; }
    header { display: flex; justify-content: space-between; border-bottom: 2px solid #111827; padding-bottom: 16px; }
    h1 { margin: 0; font-size: 28px; }
    .right { text-align: right; }
    .muted { color: #64748b; font-size: 12px; }
    .box { border: 1px solid #cbd5e1; padding: 12px; margin-top: 18px; }
    .grid.two { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px 24px; }
    .totals { margin-left: auto; width: 320px; margin-top: 18px; }
    .totals div { display: flex; justify-content: space-between; padding: 6px 0; }
    .total { border-top: 2px solid #111827; font-weight: bold; font-size: 16px; }
    .payment-boxes { margin-top: 24px; border: 1px solid #cbd5e1; padding: 12px; }
    .pay-row { display: grid; grid-template-columns: 180px 1fr; gap: 16px; align-items: center; margin-bottom: 12px; font-weight: bold; }
    .write-box { min-height: 44px; border: 1px solid #94a3b8; }
    .notes-box { min-height: 130px; border: 1px solid #94a3b8; padding: 10px; font-weight: bold; }
    .signature { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-top: 36px; }
    .signature div { min-height: 110px; border: 1px solid #94a3b8; display: flex; align-items: flex-end; justify-content: center; padding: 10px; font-size: 12px; color: #475569; }
    @media print { body { margin: 18mm; } .no-print { display: none; } }
"""

    def _receipt_folio(self, doc: dict) -> str:
        folio = str(doc.get("folio") or "").strip()
        return f"COB-{folio}" if folio else "COB-SIN-FOLIO"

    def _brand(self, context: dict) -> str:
        return str(context.get("document_brand") or context.get("brand_name") or "PLATINO").strip()

    def _money(self, value) -> str:
        return f"${float(value or 0):,.2f}"

    def _sales_context(self, context: dict) -> dict:
        schema = str(context.get("schema_ventas") or context.get("sales_schema") or context.get("schema") or "").strip()
        if not schema:
            return {"ok": False, "error": "schema_ventas/sales_schema requerido"}
        return {"ok": True, "data": {**context, "schema": schema}}
