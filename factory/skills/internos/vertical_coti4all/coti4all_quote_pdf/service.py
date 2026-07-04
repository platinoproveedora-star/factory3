from __future__ import annotations
import re
from datetime import datetime
from html import escape
from factory.engine import SupabaseClient


_VALID_SCHEMA = re.compile(r"^[a-z][a-z0-9_]*$")


class Coti4AllQuotePdfService:
    def ejecutar(self, context: dict) -> dict:
        ctx = self._tenant_context(context)
        if not ctx.get("ok"):
            return ctx
        ctx = ctx["data"]

        quote_id = str(context.get("quote_id") or context.get("id") or "").strip()
        folio = str(context.get("external_ref") or context.get("folio") or "").strip()
        if not quote_id and not folio:
            quote = context.get("quote") or {}
            if not isinstance(quote, dict):
                return {"ok": False, "error": "quote_id, folio o quote requerido"}
            doc, items = self._doc_from_context(quote)
            html = self._html(ctx, doc, items)
            return {"ok": True, "data": {"folio": doc.get("external_ref"), "filename": "cotizacion-preview.html", "html": html}}

        if context.get("dry_run", True):
            return {
                "ok": True,
                "message": "dry_run — sin consulta Supabase",
                "data": {"schema": ctx["schema"], "quote_id": quote_id or None, "folio": folio or None},
            }

        doc_res = self._find_quote(ctx, quote_id, folio)
        if not isinstance(doc_res, dict) or not doc_res.get("ok"):
            return doc_res if isinstance(doc_res, dict) else {"ok": False, "error": "bad response"}
        doc = (doc_res.get("data") or [{}])[0] if isinstance(doc_res.get("data"), list) else (doc_res.get("data") or {})
        items = doc_res.get("extra", {}).get("items") or []
        html = self._html(ctx, doc, items)
        filename = f"cotizacion-{folio or doc.get('id','tmp')}.html"
        return {"ok": True, "data": {"folio": doc.get("folio") or doc.get("external_ref"), "filename": filename, "html": html}}

    def _find_quote(self, ctx: dict, quote_id: str, folio: str) -> dict:
        q_filters = {"empresa_id": ctx["company_id"]}
        if quote_id:
            q_filters["id"] = f"eq.{quote_id}"
        if folio:
            q_filters["folio"] = f"eq.{folio}"
        res = SupabaseClient(ctx).rest_select(
            "quotes",
            filters=q_filters,
            select="id,folio,created_at,moneda,subtotal,impuesto,total,client_nombre,client_email,notas",
            limit=1,
        )
        if not res.get("ok"):
            return res
        rows = res.get("data") or []
        if not rows:
            return {"ok": False, "error": "quote no encontrado"}
        doc = rows[0]
        if not doc.get("folio"):
            doc["folio"] = folio or doc.get("id")
        items_res = SupabaseClient(ctx).rest_select(
            "quote_items",
            filters={"quote_id": f"eq.{doc['id']}"},
            select="sku,nombre,cantidad,unidad,precio_unitario,impuesto_pct,line_subtotal,line_impuesto,line_total,notas",
            order="created_at.asc",
            limit=500,
        )
        if not items_res.get("ok"):
            return items_res
        items = items_res.get("data") or []
        return {"ok": True, "data": doc, "extra": {"items": items}}

    def _tenant_context(self, context: dict) -> dict:
        schema = str(context.get("schema") or "").strip()
        if not schema or not _VALID_SCHEMA.match(schema):
            return {"ok": False, "error": "schema requerida y valida (ej: coti4all)"}
        company_id = str(context.get("company_id") or context.get("empresa_id") or "").strip()
        if not company_id:
            return {"ok": False, "error": "company_id requerido"}
        context["schema"] = schema
        context.setdefault("company_id", company_id)
        return {"ok": True, "data": context}

    def _doc_from_context(self, quote: dict) -> tuple[dict, list]:
        items_in = quote.get("items") or quote.get("lineas") or []
        items = []
        subtotal = 0.0
        vat_total = 0.0
        for raw in items_in if isinstance(items_in, list) else []:
            qty = float(raw.get("quantity") or raw.get("cantidad") or 0)
            price = float(raw.get("price") or raw.get("unit_price_ex_vat") or raw.get("precio_unitario") or 0)
            unit = str(raw.get("unit") or raw.get("unidad") or "PZA").strip() or "PZA"
            vat_rate = float(raw.get("vat_rate") or 0.16)
            line_subtotal = qty * price
            vat_amount = line_subtotal * vat_rate
            subtotal += line_subtotal
            vat_total += vat_amount
            items.append(
                {
                    "product_code": raw.get("product_code") or raw.get("producto_id") or raw.get("sku") or raw.get("nombre") or "ITEM",
                    "quantity": qty,
                    "unit_price_ex_vat": price,
                    "unit": unit,
                    "vat_rate": vat_rate,
                    "line_subtotal": line_subtotal,
                    "vat_amount": vat_amount,
                    "line_total": line_subtotal + vat_amount,
                    "notes": raw.get("notes") or raw.get("notas"),
                }
            )
        valid_days = int(quote.get("valid_days") or quote.get("validez_dias") or 30)
        today = datetime.now().date()
        doc = {
            "id": "preview",
            "external_ref": quote.get("external_ref") or quote.get("folio") or "PREVIEW",
            "quote_date": quote.get("quote_date") or today.isoformat(),
            "valid_until": quote.get("valid_until") or "",
            "currency": quote.get("currency") or quote.get("moneda") or "MXN",
            "subtotal": subtotal,
            "vat_amount": vat_total,
            "total": subtotal + vat_total,
            "customer_name": quote.get("customer_name") or quote.get("cliente_nombre") or "",
            "customer_email": quote.get("customer_email") or quote.get("cliente_email") or "",
            "notes": quote.get("notes") or quote.get("notas") or f"Validez: {valid_days} dias",
        }
        return doc, items

    def _html(self, context: dict, doc: dict, items: list) -> str:
        rows = "\n".join(
            f"""
            <tr>
              <td>{idx}</td>
              <td>{escape(str(i.get('product_code') or i.get('sku') or ''))}</td>
              <td class="num">{float(i.get('quantity') or i.get('cantidad') or 0):.2f}</td>
              <td class="num">{self._money(i.get('unit_price_ex_vat') or i.get('precio_unitario'))}</td>
              <td>{escape(str(i.get('unit') or i.get('unidad') or 'PZA'))}</td>
              <td class="num">{self._money(i.get('line_subtotal'))}</td>
              <td class="num">{self._money(i.get('vat_amount') or i.get('line_impuesto'))}</td>
              <td class="num">{self._money(i.get('line_total'))}</td>
            </tr>
            """
            for idx, i in enumerate(items, start=1)
        )
        brand = str(context.get("document_brand") or context.get("brand_name") or "Coti4All").strip()
        folio_out = escape(str(doc.get("folio") or doc.get("external_ref") or doc.get("id") or ""))
        quote_date = escape(str(doc.get("quote_date") or doc.get("created_at") or ""))
        valid_until = escape(str(doc.get("valid_until") or ""))
        customer_name = escape(str(doc.get("customer_name") or doc.get("client_nombre") or "-"))
        customer_email = escape(str(doc.get("customer_email") or doc.get("client_email") or "-"))
        currency = escape(str(doc.get("currency") or doc.get("moneda") or "MXN"))
        vat_total = self._money(doc.get("vat_amount") or doc.get("impuesto"))
        notes = escape(str(doc.get("notes") or doc.get("notas") or ""))
        return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8"/>
<title>Cotizacion {folio_out}</title>
<style>body{{font-family:Arial,sans-serif;color:#111827;margin:28px}}header{{display:flex;justify-content:space-between;border-bottom:2px solid #111827;padding-bottom:14px}}h1{{margin:0;font-size:24px}}.right{{text-align:right}}.muted{{color:#64748b;font-size:12px}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:16px}}.box{{border:1px solid #cbd5e1;padding:12px}}table{{width:100%;border-collapse:collapse;margin-top:18px;font-size:12px}}th{{background:#f1f5f9;text-align:left}}th,td{{border:1px solid #cbd5e1;padding:7px;vertical-align:top}}.num{{text-align:right}}.totals{{margin-left:auto;width:320px;margin-top:18px;border:1px solid #e2e8f0;border-radius:6px;padding:12px;background:#f8fafc}}.totals div{{display:flex;justify-content:space-between;padding:6px 0}}.total{{border-top:2px solid #111827;font-weight:bold;font-size:16px}}.seal{{margin-top:18px;padding:12px;border:2px dashed #16a34a;background:#f0fdf4;font-size:12px}}@media print{{body {{ margin: 16mm }} .no-print {{ display: none }} }}</style>
</head>
<body><button class="no-print" onclick="window.print()">Imprimir / PDF</button><header><div><h1>{escape(str(brand))}</h1><p class="muted">Cotizacion sellable</p></div><div class="right"><h1>Cotizacion {folio_out}</h1><p class="muted">Fecha: {quote_date}</p><p class="muted">Vencimiento: {valid_until}</p></div></header><section class="grid"><div class="box"><strong>Cliente:</strong> {customer_name}<br/><strong>Correo:</strong> {customer_email}</div><div class="box"><strong>Moneda:</strong> {currency}<br/><strong>Folio:</strong> {folio_out}</div></section><table><thead><tr><th>#</th><th>Codigo</th><th class="num">Cant.</th><th class="num">Sin IVA</th><th>Unidad</th><th class="num">Base</th><th class="num">IVA</th><th class="num">Total</th></tr></thead><tbody>{rows}</tbody></table><section class="totals"><div><span>Subtotal</span><span>{self._money(doc.get('subtotal'))}</span></div><div><span>IVA</span><span>{vat_total}</span></div><div class="total"><span>Total</span><span>{self._money(doc.get('total'))}</span></div></section><section class="box"><strong>Notas:</strong> {notes}</section><section class="seal"><strong>Sello / verifica:</strong> folio {folio_out} - generado {datetime.now().isoformat()} - {escape(str(brand))}</section></body></html>"""

    def _money(self, value) -> str:
        return f"${float(value or 0):,.2f}"
