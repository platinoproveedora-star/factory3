from __future__ import annotations

from datetime import datetime, timezone

from factory.engine import SupabaseClient


class ErpComprasPurchasePaymentApplyService:
    def ejecutar(self, context: dict) -> dict:
        source_folio = str(context.get("source_folio") or "").strip()
        if not source_folio:
            return {"ok": False, "error": "source_folio requerido"}

        ctx = self._schema_context(context)
        if not ctx.get("ok"):
            return ctx
        ctx = ctx["data"]

        db = SupabaseClient(ctx)
        rows_res = db.rest_select(
            "erp_kardex",
            filters={"source_type": "compra", "source_folio": source_folio},
            select="*",
            order="created_at.asc",
            limit=500,
        )
        if not rows_res.get("ok"):
            return rows_res
        rows = rows_res.get("data") or []
        rows = [row for row in rows if not self._is_canceled(row)]
        if not rows:
            return {"ok": False, "error": f"compra no encontrada o cancelada: {source_folio}"}

        total = round(sum(float(row.get("total_cost") or 0) for row in rows), 2)
        current_paid = round(sum(float(row.get("paid_amount") or 0) for row in rows), 2)
        current_balance = round(max(total - current_paid, 0), 2)
        if current_balance <= 0:
            return {"ok": False, "error": "la compra ya esta pagada"}

        raw_amount = context.get("payment_amount")
        amount = current_balance if raw_amount in (None, "") else round(float(raw_amount or 0), 2)
        if amount <= 0:
            return {"ok": False, "error": "payment_amount debe ser mayor a cero"}
        if amount > current_balance + 0.01:
            return {"ok": False, "error": "payment_amount excede el saldo pendiente"}

        new_paid_total = round(current_paid + amount, 2)
        planned = self._plan(rows, new_paid_total)
        summary = self._summary(source_folio, rows, total, current_paid, amount, planned)
        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run: no se aplico pago", "data": summary}

        timestamp = datetime.now(timezone.utc).isoformat()
        for item in planned:
            row = item["row"]
            metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
            payments = metadata.get("purchase_payments") if isinstance(metadata.get("purchase_payments"), list) else []
            payments.append(
                {
                    "applied_at": timestamp,
                    "payment_amount": amount,
                    "payment_method": self._blank(context.get("payment_method")),
                    "payment_reference": self._blank(context.get("payment_reference")),
                    "notes": self._blank(context.get("notes")),
                }
            )
            metadata.update(
                {
                    "purchase_paid_total": summary["paid_amount"],
                    "purchase_balance_amount": summary["balance_amount"],
                    "purchase_payment_status": summary["payment_status"],
                    "purchase_last_payment_at": timestamp,
                    "purchase_payments": payments,
                }
            )
            update = db.rest_update(
                "erp_kardex",
                {
                    "paid_amount": item["paid_amount"],
                    "balance_amount": item["balance_amount"],
                    "payment_status": item["payment_status"],
                    "metadata": metadata,
                    "updated_at": timestamp,
                },
                {"id": row.get("id")},
            )
            if not update.get("ok"):
                return update

        return {"ok": True, "data": summary}

    def _plan(self, rows: list[dict], new_paid_total: float) -> list[dict]:
        remaining = round(new_paid_total, 2)
        planned = []
        for row in rows:
            line_total = round(float(row.get("total_cost") or 0), 2)
            line_paid = round(min(max(remaining, 0), line_total), 2)
            remaining = round(max(remaining - line_paid, 0), 2)
            line_balance = round(max(line_total - line_paid, 0), 2)
            planned.append(
                {
                    "row": row,
                    "folio": row.get("folio"),
                    "paid_amount": line_paid,
                    "balance_amount": line_balance,
                    "payment_status": "pagado" if line_balance <= 0 and line_total else "parcial" if line_paid > 0 else "pendiente",
                }
            )
        return planned

    def _summary(self, source_folio: str, rows: list[dict], total: float, current_paid: float, amount: float, planned: list[dict]) -> dict:
        paid = round(sum(item["paid_amount"] for item in planned), 2)
        balance = round(max(total - paid, 0), 2)
        return {
            "source_folio": source_folio,
            "supplier_name_snapshot": rows[0].get("supplier_name_snapshot"),
            "movement_date": rows[0].get("movement_date"),
            "line_count": len(rows),
            "total_cost": total,
            "previous_paid_amount": current_paid,
            "payment_amount": amount,
            "paid_amount": paid,
            "balance_amount": balance,
            "payment_status": "pagado" if balance <= 0 and total else "parcial" if paid > 0 else "pendiente",
            "lines": [{k: v for k, v in item.items() if k != "row"} for item in planned],
        }

    def _is_canceled(self, row: dict) -> bool:
        metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
        return bool(metadata.get("canceled"))

    def _blank(self, value):
        value = str(value or "").strip()
        return value or None

    def _schema_context(self, context: dict) -> dict:
        schema = str(context.get("schema") or context.get("supabase_schema") or context.get("inventory_schema") or "").strip()
        company_id = str(context.get("company_id") or context.get("empresa_id") or "").strip()
        project_code = str(context.get("project_code") or context.get("inventory_project_code") or "").strip()
        missing = [k for k, v in {"schema": schema, "company_id": company_id, "project_code": project_code}.items() if not v]
        if missing:
            return {"ok": False, "error": f"contexto ERP de compras incompleto: {', '.join(missing)}"}
        return {
            "ok": True,
            "data": {
                **context,
                "schema": schema,
                "company_id": company_id,
                "empresa_id": company_id,
                "project_code": project_code,
                "module_code": "compras",
            },
        }
