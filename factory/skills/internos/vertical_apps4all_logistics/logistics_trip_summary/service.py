from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _shared import attach_orders_to_trips, list_orders, list_trip_orders, list_trips, resolve_context


class LogisticsTripSummaryService:
    def ejecutar(self, context: dict) -> dict:
        ctx_result = resolve_context(context)
        if not ctx_result.get("ok"):
            return ctx_result
        ctx = ctx_result["data"]
        trip_id = str(context.get("trip_id") or "").strip()
        trips = [trip for trip in list_trips(ctx, include_cancelled=True) if not trip_id or str(trip.get("id")) == trip_id]
        orders = list_orders(ctx, limit=1000)
        trip_orders = list_trip_orders(ctx)
        enriched = attach_orders_to_trips(trips, orders, trip_orders)
        return {"ok": True, "data": {"trips": enriched, "trip": enriched[0] if trip_id and enriched else None}}
