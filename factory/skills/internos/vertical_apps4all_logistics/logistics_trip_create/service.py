from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _shared import ACTIVE_TRIP_STATUS, db, is_dry_run, list_orders, list_trip_orders, list_trips, now_iso, reserve_folio, reserve_folios, resolve_context, table_filters


class LogisticsTripCreateService:
    def ejecutar(self, context: dict) -> dict:
        ctx_result = resolve_context(context)
        if not ctx_result.get("ok"):
            return ctx_result
        ctx = ctx_result["data"]
        folio_result = reserve_folio(ctx, "logistics_trips", "VIA") if not is_dry_run(context) else {"ok": True, "data": {"folio": "VIA-DRYRUN"}}
        if not folio_result.get("ok"):
            return folio_result
        row = {
            "folio": folio_result["data"]["folio"],
            "empresa_id": ctx["company_id"],
            "project_code": ctx["project_code"],
            "module_code": ctx["module_code"],
            "fecha_viaje": context.get("fecha_viaje") or None,
            "hora_inicio": context.get("hora_inicio") or None,
            "duracion_minutos": int(context.get("duracion_minutos") or ctx.get("duration_minutes_default") or 120),
            "vehiculo_id": context.get("vehiculo_id") or None,
            "driver_id": context.get("driver_id") or None,
            "estado": "borrador",
            "notes": context.get("notes") or None,
            "metadata": {"created_by": context.get("user_id") or context.get("created_by_user_id")},
            "created_by_user_id": context.get("user_id") or context.get("created_by_user_id"),
        }
        if is_dry_run(context):
            return {"ok": True, "message": "dry_run: no se creo viaje", "data": {"trip": row, "pedido_ids": context.get("pedido_ids") or []}}
        created = db(ctx).rest_insert("logistics_trips", row)
        if not created.get("ok"):
            return created
        trip = (created.get("data") or [{}])[0]
        pedido_ids = list(dict.fromkeys(str(item) for item in (context.get("pedido_ids") or []) if str(item).strip()))
        available_by_id = {str(order.get("id")): order for order in list_orders(ctx, limit=1000)}
        invalid = [pedido_id for pedido_id in pedido_ids if pedido_id not in available_by_id]
        if invalid:
            return {"ok": False, "error": "pedido no disponible para viaje", "data": {"pedido_ids": invalid}}
        self._remove_existing_active_assignments(ctx, pedido_ids)
        folios_result = reserve_folios(ctx, "logistics_trip_orders", "VIAP", len(pedido_ids))
        if not folios_result.get("ok"):
            return folios_result
        folios = folios_result["data"]["folios"]
        links = []
        for index, pedido_id in enumerate(pedido_ids, start=1):
            order = available_by_id[pedido_id]
            links.append(
                {
                    "folio": folios[index - 1],
                    "empresa_id": ctx["company_id"],
                    "project_code": ctx["project_code"],
                    "module_code": ctx["module_code"],
                    "trip_id": trip["id"],
                    "pedido_id": pedido_id,
                    "pedido_folio": order.get("folio"),
                    "fecha_entrega_override": context.get("fecha_entrega_override") or None,
                    "orden_carga": index,
                    "created_at": now_iso(),
                }
            )
        if links:
            inserted = db(ctx).rest_upsert("logistics_trip_orders", links, on_conflict="trip_id,pedido_id")
            if not inserted.get("ok"):
                return inserted
        return {"ok": True, "data": {"trip": trip, "assigned_count": len(links)}}

    def _remove_existing_active_assignments(self, ctx: dict, pedido_ids: list[str]) -> None:
        active_trip_ids = {str(trip.get("id")) for trip in list_trips(ctx) if str(trip.get("estado") or "") in ACTIVE_TRIP_STATUS}
        if not active_trip_ids:
            return
        for link in list_trip_orders(ctx):
            if str(link.get("trip_id")) in active_trip_ids and str(link.get("pedido_id")) in pedido_ids:
                db(ctx).rest_delete("logistics_trip_orders", table_filters(ctx, {"id": f"eq.{link.get('id')}"}))
