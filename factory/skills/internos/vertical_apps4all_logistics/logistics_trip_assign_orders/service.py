from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _shared import ACTIVE_TRIP_STATUS, LOCKED_TRIP_STATUS, db, is_dry_run, list_trip_orders, list_trips, reserve_folios, resolve_context, table_filters


class LogisticsTripAssignOrdersService:
    def ejecutar(self, context: dict) -> dict:
        ctx_result = resolve_context(context)
        if not ctx_result.get("ok"):
            return ctx_result
        ctx = ctx_result["data"]
        trip_id = str(context.get("trip_id") or "").strip()
        pedido_ids = list(dict.fromkeys(str(item) for item in (context.get("pedido_ids") or []) if str(item).strip()))
        action = str(context.get("action") or "assign").strip()
        if not trip_id or not isinstance(pedido_ids, list):
            return {"ok": False, "error": "trip_id y pedido_ids requeridos"}
        trip_res = db(ctx).rest_select("logistics_trips", filters=table_filters(ctx, {"id": f"eq.{trip_id}"}), select="id,estado", limit=1)
        trip_rows = trip_res.get("data") or []
        if not trip_res.get("ok") or not trip_rows:
            return {"ok": False, "error": "viaje no encontrado"}
        if str(trip_rows[0].get("estado")) in LOCKED_TRIP_STATUS:
            return {"ok": False, "error": "viaje bloqueado para cambios de pedidos"}
        if is_dry_run(context):
            return {"ok": True, "message": "dry_run: no se modifico asignacion", "data": {"trip_id": trip_id, "pedido_ids": pedido_ids, "action": action}}
        if action == "remove":
            deleted = []
            for pedido_id in pedido_ids:
                res = db(ctx).rest_delete("logistics_trip_orders", table_filters(ctx, {"trip_id": f"eq.{trip_id}", "pedido_id": f"eq.{pedido_id}"}))
                if not res.get("ok"):
                    return res
                deleted.extend(res.get("data") or [])
            return {"ok": True, "data": {"removed": deleted}}
        existing_links = list_trip_orders(ctx)
        existing_target_ids = {
            str(link.get("pedido_id"))
            for link in existing_links
            if str(link.get("trip_id")) == trip_id and str(link.get("pedido_id")) in pedido_ids
        }
        preserved_by_pedido = self._preserve_existing_values(ctx, trip_id, [str(item) for item in pedido_ids], existing_links)
        self._remove_existing_active_assignments(ctx, trip_id, [str(item) for item in pedido_ids], existing_links)
        new_pedido_ids = [pedido_id for pedido_id in pedido_ids if pedido_id not in existing_target_ids]
        if not new_pedido_ids:
            return {"ok": True, "data": {"assigned": [], "already_assigned": sorted(existing_target_ids)}}
        rows = []
        folios_result = reserve_folios(ctx, "logistics_trip_orders", "VIAP", len(new_pedido_ids))
        if not folios_result.get("ok"):
            return folios_result
        folios = folios_result["data"]["folios"]
        for index, pedido_id in enumerate(new_pedido_ids, start=1):
            preserved = preserved_by_pedido.get(pedido_id) or {}
            rows.append(
                {
                    "folio": folios[index - 1],
                    "empresa_id": ctx["company_id"],
                    "project_code": ctx["project_code"],
                    "module_code": ctx["module_code"],
                    "trip_id": trip_id,
                    "pedido_id": pedido_id,
                    "peso_override_kg": context.get("peso_override_kg") if "peso_override_kg" in context else preserved.get("peso_override_kg"),
                    "fecha_entrega_override": context.get("fecha_entrega_override") if "fecha_entrega_override" in context else preserved.get("fecha_entrega_override"),
                    "orden_carga": index,
                    "notes": context.get("notes") if "notes" in context else preserved.get("notes"),
                    "metadata": preserved.get("metadata") if isinstance(preserved.get("metadata"), dict) else {},
                }
            )
        result = db(ctx).rest_insert("logistics_trip_orders", rows)
        return result if not result.get("ok") else {"ok": True, "data": {"assigned": result.get("data") or [], "already_assigned": sorted(existing_target_ids)}}

    def _preserve_existing_values(self, ctx: dict, target_trip_id: str, pedido_ids: list[str], existing_links: list[dict]) -> dict[str, dict]:
        active_trip_ids = {str(trip.get("id")) for trip in list_trips(ctx) if str(trip.get("estado") or "") in ACTIVE_TRIP_STATUS}
        preserved: dict[str, dict] = {}
        for link in existing_links:
            pedido_id = str(link.get("pedido_id") or "")
            trip_id = str(link.get("trip_id") or "")
            if pedido_id not in pedido_ids or trip_id == target_trip_id or trip_id not in active_trip_ids:
                continue
            preserved[pedido_id] = {
                "peso_override_kg": link.get("peso_override_kg"),
                "fecha_entrega_override": link.get("fecha_entrega_override"),
                "notes": link.get("notes"),
                "metadata": link.get("metadata") if isinstance(link.get("metadata"), dict) else {},
            }
        return preserved

    def _remove_existing_active_assignments(self, ctx: dict, target_trip_id: str, pedido_ids: list[str], existing_links: list[dict] | None = None) -> None:
        active_trip_ids = {str(trip.get("id")) for trip in list_trips(ctx) if str(trip.get("estado") or "") in ACTIVE_TRIP_STATUS}
        for link in (existing_links if existing_links is not None else list_trip_orders(ctx)):
            if str(link.get("trip_id")) == target_trip_id:
                continue
            if str(link.get("trip_id")) in active_trip_ids and str(link.get("pedido_id")) in pedido_ids:
                db(ctx).rest_delete("logistics_trip_orders", table_filters(ctx, {"id": f"eq.{link.get('id')}"}))
