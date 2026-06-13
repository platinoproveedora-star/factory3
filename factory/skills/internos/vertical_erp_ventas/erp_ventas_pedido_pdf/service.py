from __future__ import annotations

from html import escape

from factory.engine import SupabaseClient


class ErpVentasPedidoPdfService:
    def ejecutar(self, context: dict) -> dict:
        doc_id = str(context.get("id") or context.get("document_id") or "").strip()
        folio = str(context.get("folio") or "").strip()
        if not doc_id and not folio:
            return {"ok": False, "error": "id o folio requerido"}
        ctx = self._sales_context(context)
        if not ctx.get("ok"):
            return ctx
        ctx = ctx["data"]
        filters = {"id": doc_id} if doc_id else {"folio": folio}
        doc_res = SupabaseClient(ctx).rest_select(
            "sales_documents",
            filters={**filters, "document_type": "eq.pedido"},
            select="id,folio,external_folio,customer_name_snapshot,customer_folio_snapshot,status,document_date,due_date,delivery_address,payment_method,city,city_quadrant,total_weight_kg,subtotal,tax_total,total,balance_total,notes",
            limit=1,
        )
        if not doc_res.get("ok"):
            return doc_res
        docs = doc_res.get("data") or []
        if not docs:
            return {"ok": False, "error": "pedido no encontrado"}
        doc = docs[0]
        items_res = SupabaseClient(ctx).rest_select(
            "sales_document_items",
            filters={"document_id": doc["id"]},
            select="folio,description,quantity,unit,unit_price_ex_vat,vat_rate,vat_amount,unit_price_inc_vat,line_subtotal,weight_kg_per_unit,weight_kg_total,weight_source,line_total",
            order="created_at.asc",
            limit=500,
        )
        if not items_res.get("ok"):
            return items_res
        html = self._html(context, doc, items_res.get("data") or [])
        return {"ok": True, "data": {"folio": doc.get("folio"), "filename": f"{doc.get('folio')}.html", "html": html}}

    def _html(self, context: dict, doc: dict, items: list[dict]) -> str:
        rows = "\n".join(
            f"""
            <tr>
              <td>{idx}</td>
              <td>{escape(str(item.get('description') or ''))}<div class="muted">{escape(str(item.get('weight_source') or ''))}</div></td>
              <td class="num">{self._num(item.get('quantity'))}</td>
              <td>{escape(str(item.get('unit') or ''))}</td>
              <td class="num">{self._money(item.get('unit_price_ex_vat'))}</td>
              <td class="num">{self._pct(item.get('vat_rate'))}</td>
              <td class="num">{self._money(item.get('unit_price_inc_vat'))}</td>
              <td class="num">{self._num(item.get('weight_kg_total'))} kg</td>
              <td class="num">{self._money(item.get('line_total'))}</td>
            </tr>
            """
            for idx, item in enumerate(items, start=1)
        )
        return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <title>Pedido {escape(str(doc.get('folio') or ''))}</title>
  <style>
    body {{ font-family: Arial, sans-serif; color: #111827; margin: 28px; }}
    header {{ display: flex; justify-content: space-between; border-bottom: 2px solid #111827; padding-bottom: 14px; }}
    h1 {{ margin: 0; font-size: 26px; }}
    .right {{ text-align: right; }}
    .muted {{ color: #64748b; font-size: 12px; }}
    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 16px; }}
    .box {{ border: 1px solid #cbd5e1; padding: 12px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 18px; font-size: 12px; }}
    th {{ background: #f1f5f9; text-align: left; }}
    th, td {{ border: 1px solid #cbd5e1; padding: 7px; vertical-align: top; }}
    .num {{ text-align: right; }}
    .totals {{ margin-left: auto; width: 300px; margin-top: 18px; }}
    .totals div {{ display: flex; justify-content: space-between; padding: 6px 0; }}
    .total {{ border-top: 2px solid #111827; font-weight: bold; font-size: 16px; }}
    @media print {{ body {{ margin: 16mm; }} .no-print {{ display: none; }} }}
  </style>
</head>
<body>
  <button class="no-print" onclick="window.print()">Imprimir / guardar PDF</button>
  <header>
    <div>
      <h1>{escape(self._brand(context))}</h1>
      <p class="muted">Pedido de venta</p>
    </div>
    <div class="right">
      <h1>{escape(str(doc.get('folio') or ''))}</h1>
      <p class="muted">Fecha: {escape(str(doc.get('document_date') or ''))}</p>
      <p class="muted">Folio externo: {escape(str(doc.get('external_folio') or '-'))}</p>
    </div>
  </header>
  <section class="grid">
    <div class="box">
      <strong>Cliente:</strong> {escape(str(doc.get('customer_name_snapshot') or ''))}<br />
      <strong>Forma de pago:</strong> {escape(str(doc.get('payment_method') or ''))}<br />
      <strong>Fecha prometida:</strong> {escape(str(doc.get('due_date') or ''))}
    </div>
    <div class="box">
      <strong>Entrega:</strong> {escape(str(doc.get('delivery_address') or ''))}<br />
      <strong>Ciudad:</strong> {escape(str(doc.get('city') or ''))}<br />
      <strong>Cuadrante:</strong> {escape(str(doc.get('city_quadrant') or ''))}
    </div>
  </section>
  <table>
    <thead>
      <tr><th>#</th><th>Producto</th><th class="num">Cant.</th><th>Unidad</th><th class="num">Sin IVA</th><th class="num">IVA</th><th class="num">Con IVA</th><th class="num">Peso</th><th class="num">Total</th></tr>
    </thead>
    <tbody>{rows}</tbody>
  </table>
  <section class="totals">
    <div><span>Subtotal</span><span>{self._money(doc.get('subtotal'))}</span></div>
    <div><span>IVA</span><span>{self._money(doc.get('tax_total'))}</span></div>
    <div><span>Peso total</span><span>{self._num(doc.get('total_weight_kg'))} kg</span></div>
    <div class="total"><span>Total</span><span>{self._money(doc.get('total'))}</span></div>
  </section>
  <section class="box">
    <strong>Notas:</strong> {escape(str(doc.get('notes') or ''))}
  </section>
</body>
</html>"""

    def _sales_context(self, context: dict) -> dict:
        schema = str(context.get("schema_ventas") or context.get("sales_schema") or context.get("schema") or "").strip()
        if not schema:
            return {"ok": False, "error": "schema_ventas/sales_schema requerido"}
        return {"ok": True, "data": {**context, "schema": schema}}

    def _money(self, value) -> str:
        return f"${float(value or 0):,.2f}"

    def _num(self, value) -> str:
        return f"{float(value or 0):,.2f}"

    def _pct(self, value) -> str:
        return f"{float(value or 0) * 100:,.0f}%"

    def _brand(self, context: dict) -> str:
        return str(context.get("document_brand") or context.get("brand_name") or "PLATINO").strip()
