from __future__ import annotations

from html import escape

from factory.engine import SupabaseClient


class ErpComprasPurchasePdfService:
    def ejecutar(self, context: dict) -> dict:
        folio = str(context.get("folio") or context.get("source_folio") or "").strip()
        if not folio:
            return {"ok": False, "error": "folio requerido"}

        ctx = self._resolve_context(context)
        if not ctx.get("ok"):
            return ctx
        ctx = ctx["data"]

        rows_res = SupabaseClient(ctx).rest_select(
            "erp_kardex",
            filters={"source_folio": folio, "source_type": "compra"},
            select="*",
            order="created_at.asc",
            limit=500,
        )
        if not rows_res.get("ok"):
            return rows_res
        rows = rows_res.get("data") or []
        if not rows:
            return {"ok": False, "error": f"compra {folio} no encontrada"}

        html = self._html(folio, rows)
        return {"ok": True, "data": {"folio": folio, "filename": f"{folio}.html", "html": html}}

    def _html(self, folio: str, rows: list[dict]) -> str:
        first = rows[0]
        supplier = escape(str(first.get("supplier_name_snapshot") or "-"))
        movement_date = escape(str(first.get("movement_date") or "-"))
        external_folio = escape(str(first.get("external_folio") or "-"))
        notes = escape(str(first.get("notes") or ""))

        total_cost = 0.0
        item_rows = []
        for idx, row in enumerate(rows, start=1):
            metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
            qty = float(row.get("quantity_in") or 0)
            unit_cost = float(row.get("unit_cost") or metadata.get("lot_cost_snapshot") or 0)
            subtotal = float(metadata.get("subtotal_cost") or (qty * unit_cost))
            tax_amount = float(metadata.get("tax_amount") or 0)
            line_total = float(row.get("total_cost") or (subtotal + tax_amount))
            total_cost += line_total
            lot_code = escape(str(row.get("lot_code") or "GENERAL"))
            product = escape(str(row.get("product_name_snapshot") or "-"))
            row_notes = escape(str(row.get("notes") or ""))
            item_rows.append(f"""
              <tr>
                <td>{idx}</td>
                <td>{product}</td>
                <td>{lot_code}</td>
                <td class="num">{self._num(qty)}</td>
                <td class="num">{self._money(unit_cost)}</td>
                <td class="num">{self._money(subtotal)}</td>
                <td class="num">{self._money(tax_amount)}</td>
                <td class="num">{self._money(line_total)}</td>
                <td>{row_notes}</td>
              </tr>""")

        rows_html = "\n".join(item_rows)
        folio_esc = escape(folio)

        return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <title>Compra {folio_esc}</title>
  <style>
    body {{ font-family: Arial, sans-serif; color: #111827; margin: 32px; }}
    header {{ display: flex; justify-content: space-between; border-bottom: 2px solid #111827; padding-bottom: 16px; }}
    h1 {{ margin: 0; font-size: 28px; }}
    .right {{ text-align: right; }}
    .muted {{ color: #64748b; font-size: 12px; }}
    .box {{ border: 1px solid #cbd5e1; padding: 12px; margin-top: 18px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 18px; font-size: 12px; }}
    th {{ background: #f1f5f9; text-align: left; }}
    th, td {{ border: 1px solid #cbd5e1; padding: 7px; }}
    .num {{ text-align: right; }}
    .totals {{ margin-left: auto; width: 260px; margin-top: 18px; }}
    .totals div {{ display: flex; justify-content: space-between; padding: 6px 0; }}
    .total {{ border-top: 2px solid #111827; font-weight: bold; font-size: 16px; }}
    @media print {{ body {{ margin: 18mm; }} .no-print {{ display: none; }} }}
  </style>
</head>
<body>
  <button class="no-print" onclick="window.print()">Imprimir / guardar PDF</button>
  <header>
    <div>
      <h1>Compra / Entrada</h1>
      <p class="muted">Documento de entrada al inventario</p>
    </div>
    <div class="right">
      <h1>{folio_esc}</h1>
      <p class="muted">Fecha: {movement_date}</p>
      <p class="muted">Folio proveedor: {external_folio}</p>
    </div>
  </header>
  <section class="box">
    <strong>Proveedor:</strong> {supplier}<br />
    <strong>Notas:</strong> {notes}
  </section>
  <table>
    <thead>
      <tr>
        <th>#</th>
        <th>Producto</th>
        <th>Lote</th>
        <th class="num">Cantidad</th>
        <th class="num">Costo unit.</th>
        <th class="num">Subtotal</th>
        <th class="num">IVA</th>
        <th class="num">Total</th>
        <th>Notas</th>
      </tr>
    </thead>
    <tbody>{rows_html}</tbody>
  </table>
  <section class="totals">
    <div class="total"><span>Total compra</span><span>{self._money(total_cost)}</span></div>
  </section>
</body>
</html>"""

    def _money(self, value) -> str:
        return f"${float(value or 0):,.2f}"

    def _num(self, value) -> str:
        return f"{float(value or 0):,.4f}".rstrip("0").rstrip(".")

    def _resolve_context(self, context: dict) -> dict:
        schema = str(
            context.get("schema") or
            context.get("inventory_schema") or
            context.get("schema_inventario") or
            context.get("supabase_schema") or ""
        ).strip()
        company_id = str(context.get("company_id") or context.get("empresa_id") or "").strip()
        if not schema:
            return {"ok": False, "error": "schema requerido en context"}
        if not company_id:
            return {"ok": False, "error": "company_id requerido en context"}
        return {"ok": True, "data": {**context, "schema": schema, "company_id": company_id}}
