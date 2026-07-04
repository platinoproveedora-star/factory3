from __future__ import annotations
import re
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from factory.engine import SupabaseClient


_VALID_SCHEMA = re.compile(r"^[a-z][a-z0-9_]*$")
_Q_ = Decimal("0.01")
_FOLIO_PREFIX = "COT-"


def _dec(v, default=Decimal("0")):
    try:
        return Decimal(str(v))
    except Exception:
        return default


def _r(v: Decimal) -> Decimal:
    return v.quantize(_Q_, rounding=ROUND_HALF_UP)


class Coti4AllSalesQuoteService:
    def ejecutar(self, context: dict) -> dict:
        ctx = self._tenant_context(context)
        if not ctx.get("ok"):
            return ctx
        ctx = ctx["data"]

        action = str(context.get("action") or "upsert").strip().lower()
        external_ref = str(context.get("external_ref") or context.get("folio") or "").strip()
        quote_date = str(context.get("quote_date") or datetime.now().date().isoformat())
        currency = str(context.get("currency") or "MXN").strip().upper()
        vat_rate = _dec(context.get("vat_rate") or Decimal("0.16"), Decimal("0.16"))
        notes = str(context.get("notes") or "").strip()
        valid_days = int(context.get("valid_days") or 30)
        items_in = context.get("items") or []
        if not isinstance(items_in, list) or not items_in:
            return {"ok": False, "error": "items requerido como lista"}

        if context.get("dry_run", True):
            return {
                "ok": True,
                "message": "dry_run — sin guardar",
                "data": {
                    "schema": ctx["schema"],
                    "action": action,
                    "external_ref": external_ref or None,
                    "quote_date": quote_date,
                    "currency": currency,
                    "vat_rate": float(vat_rate),
                    "valid_days": valid_days,
                    "items_preview": len(items_in),
                },
            }

        customer_name = str(context.get("customer_name") or "").strip()
        customer_email = str(context.get("customer_email") or "").strip()
        dashboard_form = context.get("dashboard_form") if isinstance(context.get("dashboard_form"), dict) else None
        sub = Decimal("0")
        tax = Decimal("0")
        costo_total = Decimal("0")
        margen_total = Decimal("0")
        parsed = []
        for it in items_in:
            pcode = str(it.get("product_code") or it.get("product_id") or "").strip()
            if not pcode:
                continue
            pname = str(it.get("product_name") or it.get("name") or "").strip() or pcode
            qty = _dec(it.get("quantity") or it.get("qty") or 0)
            unit_price = _dec(it.get("unit_price_ex_vat") or it.get("price") or 0)
            unit_cost = _dec(it.get("unit_cost") or it.get("costo_unitario") or 0)
            unit = str(it.get("unit") or it.get("unidad") or "PZA").strip() or "PZA"
            line_sub = _r(unit_price * qty)
            line_vat = _r(line_sub * vat_rate)
            line_costo = _r(unit_cost * qty)
            line_margen = _r(line_sub - line_costo)
            sub = _r(sub + line_sub)
            tax = _r(tax + line_vat)
            costo_total = _r(costo_total + line_costo)
            margen_total = _r(margen_total + line_margen)
            parsed.append(
                {
                    "product_code": pcode,
                    "product_name": pname,
                    "quantity": float(qty),
                    "unit_price_ex_vat": float(unit_price),
                    "unit_cost": float(unit_cost),
                    "unit": unit,
                    "vat_rate": float(vat_rate),
                    "line_subtotal": float(line_sub),
                    "line_costo": float(line_costo),
                    "line_margen": float(line_margen),
                    "vat_amount": float(line_vat),
                    "line_total": float(_r(line_sub + line_vat)),
                    "notes": str(it.get("notes") or "").strip() or None,
                }
            )

        if not parsed:
            return {"ok": False, "error": "no hay items validos"}

        total = _r(sub + tax)
        margen_pct = float(_r(margen_total / sub * 100)) if sub else 0.0
        folio = external_ref or self._next_folio(ctx)
        payload = {
            "empresa_id": ctx["company_id"],
            "folio": folio,
            "project_code": ctx.get("project_code"),
            "module_code": ctx.get("module_code"),
            "client_nombre": customer_name or None,
            "client_email": customer_email or None,
            "status": "draft",
            "moneda": currency,
            "subtotal": float(sub),
            "impuesto": float(tax),
            "total": float(total),
            "costo_total": float(costo_total),
            "margen": float(margen_total),
            "margen_pct": margen_pct,
            "validez_dias": valid_days,
            "notas": notes or None,
            "metadata": {"valid_days": valid_days, "items": parsed, "dashboard_form": dashboard_form},
        }
        if action == "upsert" and external_ref:
            check = SupabaseClient(ctx).rest_select(
                "quotes",
                filters={"folio": f"eq.{external_ref}", "empresa_id": f"eq.{ctx['company_id']}"},
                select="id",
                limit=1,
            )
            rows = check.get("data") or []
            if rows:
                action = "update"
                existing_id = rows[0].get("id")
                upd = dict(payload)
                upd.pop("id", None)
                res = SupabaseClient(ctx).rest_update("quotes", values=upd, filters={"id": f"eq.{existing_id}"})
                if not res.get("ok"):
                    return res
                item_res = self._replace_items(ctx, existing_id, payload["folio"], parsed, replace=True)
                if not item_res.get("ok"):
                    return item_res
                return self._wrap_draft(ctx, action, res, parsed, total, sub, tax, costo_total, margen_total, margen_pct, existing_id, payload["folio"])

        res = SupabaseClient(ctx).rest_insert("quotes", payload)
        quote_rows = res.get("data") or []
        quote_id = quote_rows[0].get("id") if quote_rows else None
        if quote_id:
            item_res = self._replace_items(ctx, quote_id, payload["folio"], parsed)
            if not item_res.get("ok"):
                return item_res
        return self._wrap_draft(ctx, action, res, parsed, total, sub, tax, costo_total, margen_total, margen_pct, quote_id, payload["folio"])

    def _next_folio(self, ctx: dict) -> str:
        res = SupabaseClient(ctx).rest_select(
            "quotes",
            filters={"empresa_id": f"eq.{ctx['company_id']}", "folio": f"like.{_FOLIO_PREFIX}*"},
            select="folio",
            order="folio.desc",
            limit=1,
        )
        rows = (res.get("data") or []) if res.get("ok") else []
        last_n = 0
        if rows:
            match = re.search(r"(\d+)$", str(rows[0].get("folio") or ""))
            if match:
                last_n = int(match.group(1))
        return f"{_FOLIO_PREFIX}{last_n + 1:04d}"

    def _replace_items(self, ctx, quote_id: str, quote_folio: str, items: list[dict], replace: bool = False) -> dict:
        if replace:
            del_res = SupabaseClient(ctx).rest_delete("quote_items", filters={"quote_id": f"eq.{quote_id}"})
            if not del_res.get("ok"):
                return del_res
        rows = []
        for idx, item in enumerate(items, start=1):
            line_subtotal = item.get("line_subtotal") or 0
            line_margen = item.get("line_margen") or 0
            rows.append(
                {
                    "quote_id": quote_id,
                    "empresa_id": ctx["company_id"],
                    "folio": f"{quote_folio}-{idx:03d}",
                    "sku": item.get("product_code"),
                    "nombre": item.get("product_name") or item.get("product_code") or "Item",
                    "cantidad": item.get("quantity"),
                    "unidad": item.get("unit") or "PZA",
                    "precio_unitario": item.get("unit_price_ex_vat"),
                    "costo_unitario": item.get("unit_cost"),
                    "line_subtotal": line_subtotal,
                    "line_costo": item.get("line_costo") or 0,
                    "line_margen": line_margen,
                    "line_margen_pct": round((line_margen / line_subtotal) * 100, 3) if line_subtotal else 0,
                    "impuesto_pct": item.get("vat_rate"),
                    "line_impuesto": item.get("vat_amount"),
                    "line_total": item.get("line_total"),
                    "notas": item.get("notes"),
                    "orden": idx,
                }
            )
        if not rows:
            return {"ok": True, "data": []}
        return SupabaseClient(ctx).rest_insert("quote_items", rows)

    def _wrap_draft(self, ctx, action, res, items, total, subtotal, tax, costo_total, margen_total, margen_pct, quote_id=None, folio=None):
        if not res.get("ok"):
            return res
        return {
            "ok": True,
            "message": f"Cotizacion guardada: {action}",
            "schema": ctx["schema"],
            "data": {
                "company_id": ctx["company_id"],
                "quote_id": quote_id,
                "folio": folio,
                "action": action,
                "totals": {
                    "subtotal": float(subtotal),
                    "vat_amount": float(tax),
                    "total": float(total),
                    "costo_total": float(costo_total),
                    "margen": float(margen_total),
                    "margen_pct": margen_pct,
                    "currency": "MXN",
                },
                "items": items,
            },
        }

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
