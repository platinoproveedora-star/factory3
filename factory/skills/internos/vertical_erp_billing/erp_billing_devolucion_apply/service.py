from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import SupabaseClient, blank, fetch_one, identity_row, insert_event, money, reserve_folio, resolve_billing_context, sales_context, utc_now  # noqa: E402


class ErpBillingDevolucionApplyService:
    def ejecutar(self, context: dict) -> dict:
        ctx_result = resolve_billing_context(context)
        if not ctx_result.get("ok"):
            return ctx_result
        ctx = ctx_result["data"]

        dev_id = blank(context.get("devolucion_id") or context.get("devolucion_folio"))
        if not dev_id:
            return {"ok": False, "error": "devolucion_id o devolucion_folio requerido"}

        filters = {"id": dev_id} if len(dev_id) > 20 else {"folio": dev_id}
        devolucion = fetch_one(SupabaseClient(ctx), "billing_devoluciones", filters)
        if not devolucion:
            return {"ok": False, "error": "devolucion no encontrada"}
        if devolucion.get("status") == "aplicada":
            return {"ok": False, "error": "la devolucion ya fue aplicada"}

        resolution = str(context.get("resolution") or "abono_remision").strip()
        if resolution not in {"abono_remision", "anticipo"}:
            return {"ok": False, "error": "resolution debe ser 'abono_remision' o 'anticipo'"}

        amount = money(devolucion.get("amount"))
        billing_db = SupabaseClient(ctx)

        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run: no se aplico devolucion", "data": {"resolution": resolution, "amount": amount}}

        if resolution == "anticipo":
            # Convertir en anticipo disponible
            folio_result = reserve_folio(ctx, "billing_anticipos", "ANT")
            if not folio_result.get("ok"):
                return folio_result
            anticipo_row = {
                **identity_row(ctx),
                "folio": folio_result["data"]["folio"],
                "customer_id": blank(devolucion.get("customer_id")),
                "customer_name": devolucion.get("customer_name"),
                "amount": amount,
                "unapplied_amount": amount,
                "payment_method": "other",
                "status": "disponible",
                "notes": f"Generado por devolución {devolucion.get('folio')}",
                "metadata": {"devolucion_id": devolucion.get("id"), "devolucion_folio": devolucion.get("folio")},
            }
            ant_result = billing_db.rest_insert("billing_anticipos", anticipo_row)
            if not ant_result.get("ok"):
                return ant_result
            ant_data = ant_result.get("data") or []
            anticipo = ant_data[0] if isinstance(ant_data, list) and ant_data else ant_data
            billing_db.rest_update("billing_devoluciones", {"status": "aplicada", "resolution": "anticipo", "anticipo_id": anticipo.get("id"), "updated_at": utc_now()}, {"id": devolucion["id"]})
            insert_event(ctx, "devolucion_applied_anticipo", {"devolucion_id": devolucion["id"], "anticipo_id": anticipo.get("id")}, False)
            return {"ok": True, "data": {"resolution": "anticipo", "anticipo_folio": anticipo.get("folio"), "amount": amount}}

        # Abonar a la remision original
        sales_ctx_result = sales_context(ctx)
        if not sales_ctx_result.get("ok"):
            return {"ok": False, "error": "sales_schema requerido para abonar a remision"}
        sales_ctx = sales_ctx_result["data"]

        doc_id = blank(devolucion.get("sales_document_id"))
        if not doc_id:
            return {"ok": False, "error": "la devolucion no tiene remision vinculada — usa resolution='anticipo'"}

        document = fetch_one(SupabaseClient(sales_ctx), "sales_documents", {"id": doc_id}, "id,folio,total,paid_total,balance_total,status")
        if not document:
            return {"ok": False, "error": "remision vinculada no encontrada"}

        new_balance = max(money(document.get("balance_total") if document.get("balance_total") is not None else document.get("total")) - amount, 0)
        new_paid = money(document.get("total")) - new_balance
        doc_status = "pagada" if new_balance <= 0 else ("parcial" if new_paid > 0 else "pendiente")

        SupabaseClient(sales_ctx).rest_update("sales_documents", {"paid_total": new_paid, "balance_total": new_balance, "status": doc_status, "updated_at": utc_now()}, {"id": doc_id})
        billing_db.rest_update("billing_devoluciones", {"status": "aplicada", "resolution": "abono_remision", "updated_at": utc_now()}, {"id": devolucion["id"]})
        insert_event(ctx, "devolucion_applied_remision", {"devolucion_id": devolucion["id"], "document_id": doc_id, "amount": amount}, False)
        return {"ok": True, "data": {"resolution": "abono_remision", "sales_folio": document.get("folio"), "new_balance": new_balance, "amount": amount}}
