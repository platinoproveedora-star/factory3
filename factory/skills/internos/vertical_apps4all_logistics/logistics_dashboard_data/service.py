from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _shared import ACTIVE_TRIP_STATUS, attach_orders_to_trips, list_catalogs, list_orders, list_trip_orders, list_trips, resolve_context


class LogisticsDashboardDataService:
    def ejecutar(self, context: dict) -> dict:
        ctx_result = resolve_context(context)
        if not ctx_result.get("ok"):
            return ctx_result
        ctx = ctx_result["data"]
        limit = min(max(int(context.get("limit") or 500), 1), 1000)
        orders = list_orders(ctx, limit=limit)
        trips = list_trips(ctx)
        trip_orders = list_trip_orders(ctx)
        trips_by_id = {str(trip.get("id")): trip for trip in trips}
        assignment_by_order = {}
        for link in trip_orders:
            trip = trips_by_id.get(str(link.get("trip_id")))
            if not trip or str(trip.get("estado") or "") not in ACTIVE_TRIP_STATUS:
                continue
            assignment_by_order[str(link.get("pedido_id"))] = {
                "trip_id": trip.get("id"),
                "trip_folio": trip.get("folio"),
                "trip_estado": trip.get("estado"),
                "fecha_viaje": trip.get("fecha_viaje"),
                "hora_inicio": trip.get("hora_inicio"),
            }
        available_orders = [{**order, "logistics_assignment": assignment_by_order.get(str(order.get("id")))} for order in orders]
        enriched_trips = attach_orders_to_trips(trips, orders, trip_orders)
        return {
            "ok": True,
            "data": {
                "company_id": ctx["company_id"],
                "project_code": ctx["project_code"],
                "module_code": ctx["module_code"],
                "schema": ctx["schema"],
                "sales_schema": ctx["sales_schema"],
                "key_products": ctx.get("key_products") or [],
                "duration_minutes_default": ctx.get("duration_minutes_default") or 120,
                "available_orders": available_orders,
                "trips": enriched_trips,
                "trip_orders": trip_orders,
                "catalogs": list_catalogs(ctx),
            },
        }
