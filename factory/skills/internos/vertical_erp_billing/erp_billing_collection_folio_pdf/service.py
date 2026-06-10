from __future__ import annotations

import sys
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import SupabaseClient, blank, fetch_one, resolve_billing_context, today_iso  # noqa: E402


class ErpBillingCollectionFolioPdfService:
    def ejecutar(self, context: dict) -> dict:
        ctx_result = resolve_billing_context(context)
        if not ctx_result.get("ok"):
            return ctx_result
        ctx = ctx_result["data"]
        folio = self._load_folio(ctx, context)
        if not folio:
            return {"ok": False, "error": "folio de cobranza no encontrado"}
        html = self._html(context, folio)
        return {"ok": True, "data": {"folio": folio.get("folio"), "filename": f"{folio.get('folio')}.html", "html": html}}

    def _load_folio(self, ctx: dict, context: dict) -> dict | None:
        folio_id = blank(context.get("id") or context.get("collection_folio_id"))
        folio = blank(context.get("folio") or context.get("collection_folio"))
        if not folio_id and not folio:
            direct = context.get("collection_folio_data")
            return direct if isinstance(direct, dict) else None
        filters = {"id": folio_id} if folio_id else {"folio": folio}
        return fetch_one(SupabaseClient(ctx), "billing_collection_folios", filters)

    def _html(self, context: dict, folio: dict) -> str:
        brand = escape(str(context.get("document_brand") or context.get("brand_name") or "PLATINO"))
        today = escape(str(context.get("print_date") or today_iso()))
        return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <title>Folio de cobranza {escape(str(folio.get('folio') or ''))}</title>
  <style>
    body {{ font-family: Arial, sans-serif; color: #111827; margin: 32px; }}
    header {{ display: flex; justify-content: space-between; border-bottom: 2px solid #111827; padding-bottom: 14px; }}
    h1 {{ margin: 0; font-size: 26px; }}
    .muted {{ color: #64748b; font-size: 12px; }}
    .box {{ border: 1px solid #cbd5e1; padding: 12px; margin-top: 18px; }}
    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }}
    .write {{ min-height: 44px; border: 1px solid #94a3b8; margin-top: 6px; }}
    .notes {{ min-height: 110px; border: 1px solid #94a3b8; margin-top: 6px; }}
    .signature {{ min-height: 90px; border: 1px solid #94a3b8; display: flex; align-items: flex-end; justify-content: center; padding: 10px; }}
    @media print {{ body {{ margin: 18mm; }} .no-print {{ display: none; }} }}
  </style>
</head>
<body>
  <button class="no-print" onclick="window.print()">Imprimir / guardar PDF</button>
  <header>
    <div>
      <h1>{brand}</h1>
      <p class="muted">Folio de cobranza</p>
    </div>
    <div style="text-align:right">
      <h1>{escape(str(folio.get('folio') or ''))}</h1>
      <p class="muted">Fecha: {today}</p>
    </div>
  </header>
  <section class="box">
    <strong>Cliente:</strong> {escape(str(folio.get('customer_name') or ''))}<br />
    <strong>Documento:</strong> {escape(str(folio.get('sales_folio') or ''))}<br />
    <strong>Importe esperado:</strong> ${float(folio.get('expected_amount') or 0):,.2f}
  </section>
  <section class="box grid">
    <div><strong>Pago en efectivo</strong><div class="write"></div></div>
    <div><strong>Pago transferencia/deposito</strong><div class="write"></div></div>
    <div><strong>Importe recibido</strong><div class="write"></div></div>
    <div><strong>Referencia / rastreo</strong><div class="write"></div></div>
  </section>
  <section class="box">
    <strong>Notas</strong>
    <div class="notes"></div>
  </section>
  <section class="box grid">
    <div><strong>Nombre y firma del cliente</strong><div class="signature"></div></div>
    <div><strong>Nombre y firma del cobrador</strong><div class="signature"></div></div>
  </section>
</body>
</html>"""
