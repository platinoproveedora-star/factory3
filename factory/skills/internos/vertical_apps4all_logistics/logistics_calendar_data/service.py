from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _shared import attach_orders_to_trips, list_orders, list_trip_orders, list_trips, resolve_context


class LogisticsCalendarDataService:
    def ejecutar(self, context: dict) -> dict:
        ctx_result = resolve_context(context)
        if not ctx_result.get("ok"):
            return ctx_result
        ctx = ctx_result["data"]
        date_from = str(context.get("date_from") or "").strip()
        date_to = str(context.get("date_to") or "").strip()
        trips = [trip for trip in list_trips(ctx) if trip.get("fecha_viaje")]
        if date_from:
            trips = [trip for trip in trips if str(trip.get("fecha_viaje")) >= date_from]
        if date_to:
            trips = [trip for trip in trips if str(trip.get("fecha_viaje")) <= date_to]
        trips = [trip for trip in trips if str(trip.get("estado")) in {"programado", "confirmado", "en_ruta", "completado"}]
        enriched = attach_orders_to_trips(trips, list_orders(ctx, limit=1000), list_trip_orders(ctx))
        by_day: dict[str, list[dict]] = {}
        for trip in enriched:
            by_day.setdefault(str(trip.get("fecha_viaje")), []).append(trip)
        return {"ok": True, "data": {"days": by_day, "trips": enriched}}
