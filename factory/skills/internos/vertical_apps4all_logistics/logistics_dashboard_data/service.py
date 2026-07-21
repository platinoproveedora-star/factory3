from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _shared import active_assigned_pedido_ids, attach_orders_to_trips, list_catalogs, list_orders, list_trip_orders, list_trips, resolve_context


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
        assigned = active_assigned_pedido_ids(trips, trip_orders)
        available_orders = [order for order in orders if str(order.get("id")) not in assigned]
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
