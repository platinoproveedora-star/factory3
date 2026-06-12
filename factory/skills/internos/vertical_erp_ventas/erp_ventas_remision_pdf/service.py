from __future__ import annotations

import importlib.util
from html import escape
from pathlib import Path

from factory.engine import SupabaseClient


_SKILLS_ROOT = Path(__file__).resolve().parents[2]


class ErpVentasRemisionPdfService:
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
            filters=filters,
            select="id,folio,external_folio,customer_name_snapshot,customer_folio_snapshot,status,document_date,delivery_address,chofer,unidad,subtotal,tax_total,total,balance_total,notes",
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
        hide_prices = str(context.get("hide_prices") or "").strip().lower() in ("1", "true", "yes")
        receipt = self._receipt(context, doc)
        html = self._html(context, doc, items_res.get("data") or [], receipt, hide_prices=hide_prices)
        return {"ok": True, "data": {"folio": doc.get("folio"), "filename": f"{doc.get('folio')}.html", "html": html}}

    def _html(self, context: dict, doc: dict, items: list[dict], receipt: dict, hide_prices: bool = False) -> str:
        if hide_prices:
            rows = "\n".join(
                f"""
                <tr>
                  <td>{idx}</td>
                  <td>{escape(str(item.get('description') or ''))}</td>
                  <td class="num">{self._num(item.get('quantity'))}</td>
                  <td>{escape(str(item.get('unit') or ''))}</td>
                </tr>
                """
                for idx, item in enumerate(items, start=1)
            )
            table_header = "<tr><th>#</th><th>Producto</th><th class=\"num\">Cantidad</th><th>Unidad</th></tr>"
            totals_section = ""
        else:
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
            table_header = "<tr><th>#</th><th>Producto</th><th class=\"num\">Cantidad</th><th>Unidad</th><th class=\"num\">Precio</th><th class=\"num\">IVA</th><th class=\"num\">Importe</th></tr>"
            totals_section = f"""
  <section class="totals">
    <div><span>Subtotal</span><span>{self._money(doc.get('subtotal'))}</span></div>
    <div><span>IVA</span><span>{self._money(doc.get('tax_total'))}</span></div>
    <div class="total"><span>Total</span><span>{self._money(doc.get('total'))}</span></div>
  </section>"""

        return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <title>Remision {escape(str(doc.get('folio') or ''))} / {escape(str(receipt.get('folio') or 'Folio de cobranza'))}</title>
  <style>
    body {{ font-family: Arial, sans-serif; color: #111827; margin: 32px; }}
    header {{ display: flex; justify-content: space-between; border-bottom: 2px solid #111827; padding-bottom: 16px; }}
    h1 {{ margin: 0; font-size: 28px; }}
    .right {{ text-align: right; }}
    .muted {{ color: #64748b; font-size: 12px; }}
    .box {{ border: 1px solid #cbd5e1; padding: 12px; margin-top: 18px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 18px; font-size: 13px; }}
    th {{ background: #f1f5f9; text-align: left; }}
    th, td {{ border: 1px solid #cbd5e1; padding: 8px; }}
    .num {{ text-align: right; }}
    .totals {{ margin-left: auto; width: 280px; margin-top: 18px; }}
    .totals div {{ display: flex; justify-content: space-between; padding: 6px 0; }}
    .total {{ border-top: 2px solid #111827; font-weight: bold; font-size: 16px; }}
    .signature {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-top: 36px; }}
    .signature div {{ min-height: 110px; border: 1px solid #94a3b8; display: flex; align-items: flex-end; justify-content: center; padding: 10px; font-size: 12px; color: #475569; }}
    .receipt-page {{ break-before: page; page-break-before: always; }}
    .payment-boxes {{ margin-top: 24px; border: 1px solid #cbd5e1; padding: 12px; }}
    .pay-row {{ display: grid; grid-template-columns: 180px 1fr; gap: 16px; align-items: center; margin-bottom: 12px; font-weight: bold; }}
    .write-box {{ min-height: 44px; border: 1px solid #94a3b8; }}
    .notes-box {{ min-height: 130px; border: 1px solid #94a3b8; padding: 10px; font-weight: bold; }}
    @media print {{ body {{ margin: 18mm; }} .no-print {{ display: none; }} }}
  </style>
</head>
<body>
  <button class="no-print" onclick="window.print()">Imprimir / guardar PDF</button>
  <header>
    <div>
      <h1>{escape(self._brand(context))}</h1>
      <p class="muted">Remision de venta{' (sin precios)' if hide_prices else ''}</p>
    </div>
    <div class="right">
      <h1>{escape(str(doc.get('folio') or ''))}</h1>
      <p class="muted">Fecha: {escape(str(doc.get('document_date') or ''))}</p>
      <p class="muted">Folio externo: {escape(str(doc.get('external_folio') or '-'))}</p>
    </div>
  </header>
  <section class="box">
    <strong>Cliente:</strong> {escape(str(doc.get('customer_name_snapshot') or ''))}<br />
    <strong>Direccion de entrega:</strong> {escape(str(doc.get('delivery_address') or ''))}<br />
    <strong>Chofer:</strong> {escape(str(doc.get('chofer') or ''))}<br />
    <strong>Unidad:</strong> {escape(str(doc.get('unidad') or ''))}<br />
    <strong>Notas:</strong> {escape(str(doc.get('notes') or ''))}
  </section>
  <table>
    <thead>{table_header}</thead>
    <tbody>{rows}</tbody>
  </table>
  {totals_section}
  <section class="signature">
    <div><span>Nombre de quien recibe</span></div>
    <div><span>Firma de quien recibe</span></div>
  </section>
  {receipt.get('html') or ''}
</body>
</html>"""

    def _receipt(self, context: dict, doc: dict) -> dict:
        service_path = _SKILLS_ROOT / "vertical_erp_ventas" / "erp_ventas_folio_cobranza_pdf" / "service.py"
        spec = importlib.util.spec_from_file_location("erp_ventas_folio_cobranza_pdf_service", service_path)
        if spec is None or spec.loader is None:
            return {"folio": "", "html": ""}
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        service = module.ErpVentasFolioCobranzaPdfService()
        return {"folio": service._receipt_folio(doc), "html": service.fragment(context, doc)}

    def _money(self, value) -> str:
        return f"${float(value or 0):,.2f}"

    def _num(self, value) -> str:
        return f"{float(value or 0):,.2f}"

    def _brand(self, context: dict) -> str:
        return str(context.get("document_brand") or context.get("brand_name") or "PLATINO").strip()

    def _sales_context(self, context: dict) -> dict:
        schema = str(context.get("schema_ventas") or context.get("sales_schema") or context.get("schema") or "").strip()
        if not schema:
            return {"ok": False, "error": "schema_ventas/sales_schema requerido"}
        return {"ok": True, "data": {**context, "schema": schema}}
