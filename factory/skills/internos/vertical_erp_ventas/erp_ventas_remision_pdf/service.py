from __future__ import annotations

from html import escape

from factory.engine import SupabaseClient


class ErpVentasRemisionPdfService:
    def ejecutar(self, context: dict) -> dict:
        doc_id = str(context.get("id") or context.get("document_id") or "").strip()
        folio = str(context.get("folio") or "").strip()
        if not doc_id and not folio:
            return {"ok": False, "error": "id o folio requerido"}

        ctx = {**context, "schema": "uc101_proy002"}
        filters = {"id": doc_id} if doc_id else {"folio": folio}
        doc_res = SupabaseClient(ctx).rest_select(
            "sales_documents",
            filters=filters,
            select="id,folio,external_folio,customer_name_snapshot,customer_folio_snapshot,status,document_date,delivery_address,subtotal,tax_total,total,notes",
            limit=1,
        )
        if not doc_res.get("ok"):
            return doc_res
        docs = doc_res.get("data") or []
        if not docs:
            return {"ok": False, "error": "remision no encontrada"}
        doc = docs[0]

        items_res = SupabaseClient(ctx).rest_select(
            "sales_document_items",
            filters={"document_id": doc["id"]},
            select="folio,description,quantity,unit,unit_price,tax_amount,line_total",
            order="created_at.asc",
            limit=500,
        )
        if not items_res.get("ok"):
            return items_res
        html = self._html(doc, items_res.get("data") or [])
        return {"ok": True, "data": {"folio": doc.get("folio"), "filename": f"{doc.get('folio')}.html", "html": html}}

    def _html(self, doc: dict, items: list[dict]) -> str:
        rows = "\n".join(
            f"""
            <tr>
              <td>{idx}</td>
              <td>{escape(str(item.get('description') or ''))}</td>
              <td class="num">{self._num(item.get('quantity'))}</td>
              <td>{escape(str(item.get('unit') or ''))}</td>
              <td class="num">{self._money(item.get('unit_price'))}</td>
              <td class="num">{self._money(item.get('tax_amount'))}</td>
              <td class="num">{self._money(item.get('line_total'))}</td>
            </tr>
            """
            for idx, item in enumerate(items, start=1)
        )
        return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <title>Remision {escape(str(doc.get('folio') or ''))}</title>
  <style>
    body {{ font-family: Arial, sans-serif; color: #111827; margin: 32px; }}
    header {{ display: flex; justify-content: space-between; border-bottom: 2px solid #111827; padding-bottom: 16px; }}
    h1 {{ margin: 0; font-size: 28px; }}
    .muted {{ color: #64748b; font-size: 12px; }}
    .box {{ border: 1px solid #cbd5e1; padding: 12px; margin-top: 18px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 18px; font-size: 13px; }}
    th {{ background: #f1f5f9; text-align: left; }}
    th, td {{ border: 1px solid #cbd5e1; padding: 8px; }}
    .num {{ text-align: right; }}
    .totals {{ margin-left: auto; width: 280px; margin-top: 18px; }}
    .totals div {{ display: flex; justify-content: space-between; padding: 6px 0; }}
    .total {{ border-top: 2px solid #111827; font-weight: bold; font-size: 16px; }}
    @media print {{ body {{ margin: 18mm; }} .no-print {{ display: none; }} }}
  </style>
</head>
<body>
  <button class="no-print" onclick="window.print()">Imprimir / guardar PDF</button>
  <header>
    <div>
      <h1>DURALON</h1>
      <p class="muted">Remision de venta</p>
    </div>
    <div>
      <h1>{escape(str(doc.get('folio') or ''))}</h1>
      <p class="muted">Fecha: {escape(str(doc.get('document_date') or ''))}</p>
      <p class="muted">Folio externo: {escape(str(doc.get('external_folio') or '-'))}</p>
    </div>
  </header>
  <section class="box">
    <strong>Cliente:</strong> {escape(str(doc.get('customer_name_snapshot') or ''))}<br />
    <strong>Direccion de entrega:</strong> {escape(str(doc.get('delivery_address') or ''))}<br />
    <strong>Notas:</strong> {escape(str(doc.get('notes') or ''))}
  </section>
  <table>
    <thead>
      <tr><th>#</th><th>Producto</th><th class="num">Cantidad</th><th>Unidad</th><th class="num">Precio</th><th class="num">IVA</th><th class="num">Importe</th></tr>
    </thead>
    <tbody>{rows}</tbody>
  </table>
  <section class="totals">
    <div><span>Subtotal</span><span>{self._money(doc.get('subtotal'))}</span></div>
    <div><span>IVA</span><span>{self._money(doc.get('tax_total'))}</span></div>
    <div class="total"><span>Total</span><span>{self._money(doc.get('total'))}</span></div>
  </section>
</body>
</html>"""

    def _money(self, value) -> str:
        return f"${float(value or 0):,.2f}"

    def _num(self, value) -> str:
        return f"{float(value or 0):,.2f}"
