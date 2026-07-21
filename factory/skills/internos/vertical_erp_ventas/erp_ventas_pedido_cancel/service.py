from __future__ import annotations

import importlib.util
from datetime import datetime, timezone
from pathlib import Path

from factory.engine import SupabaseClient


_SKILLS_ROOT = Path(__file__).resolve().parents[2]
_CANCELABLE_STATUS = {"pedido", "liberado"}


def _blank(value) -> str | None:
    text = str(value or "").strip()
    return text or None


class ErpVentasPedidoCancelService:
    def ejecutar(self, context: dict) -> dict:
        doc_id = str(context.get("id") or context.get("document_id") or "").strip()
        folio = str(context.get("folio") or "").strip()
        if not doc_id and not folio:
            return {"ok": False, "error": "id o folio requerido"}

        cfg_result = self._cfg(context)
        if not cfg_result.get("ok"):
            return cfg_result
        cfg = cfg_result["data"]
        sales_ctx = self._sales_context(context, cfg)
        db = SupabaseClient(sales_ctx)

        doc = self._get_doc(db, doc_id, folio)
        if not doc:
            return {"ok": False, "error": "pedido no encontrado"}
        if str(doc.get("status") or "") not in _CANCELABLE_STATUS:
            return {"ok": False, "error": "pedido no se puede cancelar: ya esta remisionado o cancelado"}

        note = _blank(context.get("cancel_reason")) or "Cancelacion de pedido"
        now = datetime.now(timezone.utc).isoformat()
        logistics_ctx = self._logistics_context(context, cfg)

        if context.get("dry_run", True):
            return {
                "ok": True,
                "message": "dry_run: no se cancelo pedido",
                "data": {"pedido": {**doc, "status": "cancelado"}, "logistics_cleanup_planned": bool(logistics_ctx)},
            }

        metadata = doc.get("metadata") if isinstance(doc.get("metadata"), dict) else {}
        metadata = {
            **metadata,
            "canceled_at": now,
            "cancel_reason": note,
            "canceled_by_skill": "vertical_erp_ventas/erp_ventas_pedido_cancel",
        }
        update = {
            "status": "cancelado",
            "balance_total": 0,
            "metadata": metadata,
            "notes": self._append_cancel_note(doc.get("notes"), note, now),
            "updated_at": now,
        }
        updated = db.rest_update("sales_documents", update, {"id": doc["id"]})
        if not updated.get("ok"):
            return updated
        cleanup = self._cleanup_logistics_assignments(logistics_ctx, doc["id"]) if logistics_ctx else {"ok": True, "data": {"removed": []}}
        rows = updated.get("data") or []
        pedido = rows[0] if isinstance(rows, list) and rows else rows
        data = {"pedido": pedido, "logistics_cleanup": cleanup.get("data") or {}}
        if not cleanup.get("ok"):
            data["logistics_cleanup_error"] = cleanup.get("error")
        return {"ok": True, "data": data}

    def _get_doc(self, db: SupabaseClient, doc_id: str, folio: str) -> dict | None:
        filters = {"id": doc_id} if doc_id else {"folio": folio}
        result = db.rest_select(
            "sales_documents",
            filters={**filters, "document_type": "eq.pedido"},
            select="id,folio,customer_id,customer_name_snapshot,status,document_date,notes,metadata",
            limit=1,
        )
        rows = result.get("data") or []
        return rows[0] if rows else None

    def _cfg(self, context: dict) -> dict:
        service_path = _SKILLS_ROOT / "vertical_erp" / "erp_project_context_resolve" / "service.py"
        spec = importlib.util.spec_from_file_location("erp_project_context_resolve_service", service_path)
        if spec is None or spec.loader is None:
            return {"ok": False, "error": "no se pudo cargar erp_project_context_resolve"}
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        resolve_context = {
            **context,
            "module_code": context.get("module_ventas") or context.get("module_code") or "ventas",
            "schema": context.get("schema_ventas") or context.get("sales_schema") or context.get("schema"),
        }
        result = module.ErpProjectContextResolveService().ejecutar(resolve_context)
        if not result.get("ok"):
            return {"ok": False, "error": result.get("error") or "contexto ERP de ventas incompleto"}
        data = result.get("data") or {}
        cfg = {
            "empresa_id": data.get("empresa_id") or data.get("company_id"),
            "schema_ventas": data.get("sales_schema") or data.get("schema"),
            "project_ventas": data.get("project_code"),
            "module_ventas": data.get("module_code") or "ventas",
        }
        missing = [key for key, value in cfg.items() if not value]
        if missing:
            return {"ok": False, "error": f"contexto ERP de ventas incompleto: {', '.join(missing)}"}
        return {"ok": True, "data": cfg}

    def _sales_context(self, context: dict, cfg: dict) -> dict:
        return {
            **context,
            "schema": cfg["schema_ventas"],
            "company_id": cfg["empresa_id"],
            "empresa_id": cfg["empresa_id"],
            "project_code": cfg["project_ventas"],
            "module_code": cfg["module_ventas"],
        }

    def _logistics_context(self, context: dict, cfg: dict) -> dict | None:
        schema = _blank(context.get("logistics_schema") or context.get("schema_logistica"))
        project_code = _blank(context.get("logistics_project_code") or context.get("project_logistica"))
        module_code = _blank(context.get("logistics_module_code") or context.get("module_logistica"))
        if not schema or not project_code or not module_code:
            return None
        return {
            **context,
            "schema": schema,
            "company_id": cfg["empresa_id"],
            "empresa_id": cfg["empresa_id"],
            "project_code": project_code,
            "module_code": module_code,
        }

    def _cleanup_logistics_assignments(self, logistics_ctx: dict, pedido_id: str) -> dict:
        result = SupabaseClient(logistics_ctx).rest_delete(
            "logistics_trip_orders",
            {
                "empresa_id": logistics_ctx["empresa_id"],
                "project_code": logistics_ctx["project_code"],
                "module_code": logistics_ctx["module_code"],
                "pedido_id": pedido_id,
            },
        )
        if not result.get("ok"):
            return result
        return {"ok": True, "data": {"removed": result.get("data") or []}}

    def _append_cancel_note(self, previous, note: str, timestamp: str) -> str:
        suffix = f"Cancelado {timestamp}: {note}"
        previous = _blank(previous)
        return f"{previous}\n{suffix}" if previous else suffix
