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
        self._remove_existing_active_assignments(ctx, trip_id, [str(item) for item in pedido_ids])
        rows = []
        folios_result = reserve_folios(ctx, "logistics_trip_orders", "VIAP", len(pedido_ids))
        if not folios_result.get("ok"):
            return folios_result
        folios = folios_result["data"]["folios"]
        for index, pedido_id in enumerate(pedido_ids, start=1):
            rows.append(
                {
                    "folio": folios[index - 1],
                    "empresa_id": ctx["company_id"],
                    "project_code": ctx["project_code"],
                    "module_code": ctx["module_code"],
                    "trip_id": trip_id,
                    "pedido_id": pedido_id,
                    "peso_override_kg": context.get("peso_override_kg"),
                    "orden_carga": index,
                    "notes": context.get("notes"),
                }
            )
        result = db(ctx).rest_upsert("logistics_trip_orders", rows, on_conflict="trip_id,pedido_id")
        return result if not result.get("ok") else {"ok": True, "data": {"assigned": result.get("data") or []}}

    def _remove_existing_active_assignments(self, ctx: dict, target_trip_id: str, pedido_ids: list[str]) -> None:
        active_trip_ids = {str(trip.get("id")) for trip in list_trips(ctx) if str(trip.get("estado") or "") in ACTIVE_TRIP_STATUS}
        for link in list_trip_orders(ctx):
            if str(link.get("trip_id")) == target_trip_id:
                continue
            if str(link.get("trip_id")) in active_trip_ids and str(link.get("pedido_id")) in pedido_ids:
                db(ctx).rest_delete("logistics_trip_orders", table_filters(ctx, {"id": f"eq.{link.get('id')}"}))
