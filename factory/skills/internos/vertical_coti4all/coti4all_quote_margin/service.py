from __future__ import annotations
import re
from decimal import Decimal
from factory.engine import SupabaseClient


_VALID_SCHEMA = re.compile(r"^[a-z][a-z0-9_]*$")


def _dec(v, default=Decimal("0")):
    try:
        return Decimal(str(v))
    except Exception:
        return default


def _pct(num: Decimal, den: Decimal) -> float:
    if not den or den == 0:
        return 0.0
    return float((num / den * 100).quantize(Decimal("0.01")))


class Coti4AllQuoteMarginService:
    def ejecutar(self, context: dict) -> dict:
        ctx = self._tenant_context(context)
        if not ctx.get("ok"):
            return ctx
        ctx = ctx["data"]

        quote_id = str(context.get("quote_id") or context.get("id") or context.get("external_ref") or "").strip()
        if not quote_id:
            quote = context.get("quote") or {}
            items = quote.get("items") or quote.get("lineas") or []
            subtotal = sum(_dec((item.get("quantity") or item.get("cantidad") or 0)) * _dec((item.get("price") or item.get("precio_unitario") or 0)) for item in items if isinstance(item, dict))
            return {"ok": True, "data": {"totals": {"subtotal": float(subtotal), "total_cost": 0.0, "gross": float(subtotal)}, "improved_pct": 100.0 if subtotal else 0.0, "items": []}}

        if context.get("dry_run", True):
            return {
                "ok": True,
                "message": "dry_run — sin consulta Supabase",
                "data": {"schema": ctx["schema"], "quote_id": quote_id},
            }

        try:
            item_res = self._quote_items(ctx, quote_id)
            if not item_res.get("ok"):
                return item_res
            items = item_res.get("data", {}).get("items") or []
            quote = item_res.get("data", {}).get("quote") or {}
            subtotal = _dec(quote.get("subtotal") or 0)

            improve_factors = context.get("improve_factors") or {}
            total_cost = Decimal("0")
            gross = Decimal("0")
            results = []
            for it in items:
                pcode = str(it.get("sku") or "").strip()
                qty = _dec(it.get("cantidad") or 0)
                line_total = _dec(it.get("line_total") or 0)
                if not pcode:
                    continue
                facts = improve_factors.get(pcode, {})
                cost_per_unit = _dec(facts.get("cost_per_unit") or 0)
                freight_per_unit = _dec(facts.get("freight_per_unit") or 0)
                unit_cost = cost_per_unit + freight_per_unit
                line_cost = (unit_cost * qty).quantize(Decimal("0.01"), rounding="ROUND_HALF_UP")
                total_cost += line_cost
                line_gross = (line_total - line_cost).quantize(Decimal("0.01"), rounding="ROUND_HALF_UP")
                gross += line_gross
                results.append(
                    {
                        "product_code": pcode,
                        "qty": float(qty),
                        "line_total": float(line_total),
                        "unit_cost": float(unit_cost),
                        "line_cost": float(line_cost),
                        "line_gross": float(line_gross),
                    }
                )

            improved_pct = _pct(gross, subtotal)
            return {
                "ok": True,
                "schema": ctx["schema"],
                "data": {
                    "quote": {
                        "id": quote.get("id"),
                        "folio": quote.get("folio"),
                        "status": quote.get("status", "draft"),
                        "currency": quote.get("moneda", "MXN"),
                    },
                    "totals": {
                        "subtotal": float(subtotal),
                        "total_cost": float(total_cost),
                        "gross": float(gross),
                        "improved_margin_from_actual": float((gross - subtotal).quantize(Decimal("0.01"), rounding="ROUND_HALF_UP")),
                    },
                    "improved_pct": improved_pct,
                    "items": results,
                },
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _tenant_context(self, context: dict) -> dict:
        schema = str(context.get("schema") or "").strip()
        if not schema or not _VALID_SCHEMA.match(schema):
            return {"ok": False, "error": "schema requerida y valida (ej: coti4all)"}
        context["schema"] = schema
        return {"ok": True, "data": context}

    def _quote_items(self, ctx: dict, value: str) -> dict:
        q = f"eq.{value}"
        try:
            h = SupabaseClient(ctx).rest_select(
                "quotes",
                filters={"id": q},
                select="id,folio,subtotal,impuesto,total,costo_total,margen,margen_pct,status,moneda",
                limit=1,
            )
        except Exception:
            h = {"ok": False}
        if not h.get("ok"):
            return h
        h_rows = h.get("data") or []
        if not h_rows:
            h = SupabaseClient(ctx).rest_select(
                "quotes",
                filters={"folio": q},
                select="id,folio,subtotal,impuesto,total,costo_total,margen,margen_pct,status,moneda",
                limit=1,
            )
            if not h.get("ok"):
                return h
            h_rows = h.get("data") or []
        if not h_rows:
            return {"ok": False, "error": "quote no encontrado para id/folio"}
        quote_id = h_rows[0].get("id")
        i = SupabaseClient(ctx).rest_select(
            "quote_items",
            filters={"quote_id": f"eq.{quote_id}"},
            select="sku,cantidad,precio_unitario,line_subtotal,line_costo,line_margen,line_total",
            order="created_at.asc",
        )
        if not i.get("ok"):
            return i
        items = i.get("data") or []
        return {"ok": True, "data": {"quote": h_rows[0], "items": items}}
