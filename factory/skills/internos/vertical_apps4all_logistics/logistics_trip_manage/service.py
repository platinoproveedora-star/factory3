from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _shared import VALID_TRIP_STATUS, computed_status, db, is_dry_run, list_catalogs, now_iso, resolve_context, sales_db, table_filters


class LogisticsTripManageService:
    def ejecutar(self, context: dict) -> dict:
        ctx_result = resolve_context(context)
        if not ctx_result.get("ok"):
            return ctx_result
        ctx = ctx_result["data"]
        action = str(context.get("action") or "update").strip()
        if action in {"update_order_weight", "update_order_logistics"}:
            return self._update_order_logistics(ctx, context)
        trip_id = str(context.get("trip_id") or context.get("id") or "").strip()
        if not trip_id:
            return {"ok": False, "error": "trip_id requerido"}
        trip = db(ctx).rest_select("logistics_trips", filters=table_filters(ctx, {"id": f"eq.{trip_id}"}), select="*", limit=1)
        rows = trip.get("data") or []
        if not trip.get("ok") or not rows:
            return {"ok": False, "error": "viaje no encontrado"}
        current = rows[0]
        update = {}
        for key in ["fecha_viaje", "hora_inicio", "duracion_minutos", "vehiculo_id", "driver_id", "notes"]:
            if key in context:
                update[key] = context.get(key) or None
        if context.get("estado"):
            status = str(context["estado"])
            if status not in VALID_TRIP_STATUS:
                return {"ok": False, "error": "estado invalido"}
            update["estado"] = status
        else:
            update["estado"] = computed_status({**current, **update}, str(current.get("estado") or "borrador"))
        update["updated_at"] = now_iso()
        if is_dry_run(context):
            data = {"trip": {**current, **update}}
            if self._transport_changed(context):
                data["remisiones_sync_preview"] = self._sync_remisiones_transport(ctx, trip_id, {**current, **update}, dry_run=True)
            return {"ok": True, "message": "dry_run: no se actualizo viaje", "data": data}
        result = db(ctx).rest_update("logistics_trips", update, table_filters(ctx, {"id": f"eq.{trip_id}"}))
        if not result.get("ok"):
            return result
        if self._transport_changed(context):
            sync = self._sync_remisiones_transport(ctx, trip_id, {**current, **update}, dry_run=False)
            if not sync.get("ok"):
                return {"ok": False, "error": sync.get("error") or "no se pudieron sincronizar datos de transporte en remisiones", "data": {"trip_update": result, "remisiones_sync": sync}}
            return {"ok": True, "data": {"trip": result.get("data"), "remisiones_sync": sync.get("data")}}
        return result

    def _update_order_logistics(self, ctx: dict, context: dict) -> dict:
        trip_order_id = str(context.get("trip_order_id") or "").strip()
        if not trip_order_id:
            return {"ok": False, "error": "trip_order_id requerido"}
        update = {"updated_at": now_iso()}
        if "peso_override_kg" in context:
            update["peso_override_kg"] = context.get("peso_override_kg")
        if "fecha_entrega_override" in context:
            update["fecha_entrega_override"] = context.get("fecha_entrega_override") or None
        if "orden_carga" in context:
            update["orden_carga"] = context.get("orden_carga")
        if "notes" in context:
            update["notes"] = context.get("notes") or None
        if is_dry_run(context):
            return {"ok": True, "message": "dry_run: no se actualizo pedido del viaje", "data": update}
        return db(ctx).rest_update("logistics_trip_orders", update, table_filters(ctx, {"id": f"eq.{trip_order_id}"}))

    def _transport_changed(self, context: dict) -> bool:
        return "vehiculo_id" in context or "driver_id" in context

    def _sync_remisiones_transport(self, ctx: dict, trip_id: str, trip: dict, dry_run: bool) -> dict:
        transport = self._transport_payload(ctx, trip)
        orders_res = db(ctx).rest_select(
            "logistics_trip_orders",
            filters=table_filters(ctx, {"trip_id": f"eq.{trip_id}", "source_type": "eq.venta"}),
            select="pedido_id,pedido_folio,source_id,source_folio",
            limit=1000,
        )
        if not orders_res.get("ok"):
            return orders_res
        trip_orders = orders_res.get("data") or []
        pedido_ids = [str(row.get("pedido_id") or row.get("source_id") or "").strip() for row in trip_orders]
        pedido_ids = [value for value in pedido_ids if value]
        if not pedido_ids:
            return {"ok": True, "data": {"updated": 0, "skipped": 0, "transport": transport}}

        filters = {"id": f"in.({','.join(pedido_ids)})"} if len(pedido_ids) > 1 else {"id": pedido_ids[0]}
        pedidos_res = sales_db(ctx).rest_select("sales_documents", filters=filters, select="id,folio,status,metadata", limit=len(pedido_ids))
        if not pedidos_res.get("ok"):
            return pedidos_res

        updates = []
        skipped = 0
        for pedido in pedidos_res.get("data") or []:
            target = self._remision_target(pedido)
            if not target:
                skipped += 1
                continue
            if dry_run:
                updates.append({"pedido_id": pedido.get("id"), **target, **transport})
                continue
            update_res = sales_db(ctx).rest_update("sales_documents", {**transport, "updated_at": now_iso()}, target)
            if not update_res.get("ok"):
                return update_res
            updates.append({"pedido_id": pedido.get("id"), "remision": update_res.get("data")})
        return {"ok": True, "data": {"updated": len(updates), "skipped": skipped, "transport": transport, "updates": updates}}

    def _transport_payload(self, ctx: dict, trip: dict) -> dict:
        catalogs = list_catalogs(ctx)
        driver_id = str(trip.get("driver_id") or "").strip()
        vehicle_id = str(trip.get("vehiculo_id") or "").strip()
        driver = next((row for row in catalogs.get("drivers", []) if str(row.get("id")) == driver_id), None)
        vehicle = next((row for row in catalogs.get("vehicles", []) if str(row.get("id")) == vehicle_id), None)
        return {"chofer": self._blank(driver.get("nombre") if driver else None), "unidad": self._vehicle_unit(vehicle)}

    def _vehicle_unit(self, vehicle: dict | None) -> str | None:
        if not vehicle:
            return None
        name = self._blank(vehicle.get("nombre"))
        plate = self._blank(vehicle.get("placa"))
        if name and plate:
            return f"{name} - Placas {plate}"
        return name or plate

    def _remision_target(self, pedido: dict) -> dict | None:
        metadata = pedido.get("metadata") if isinstance(pedido.get("metadata"), dict) else {}
        remision_id = str(metadata.get("remision_id") or metadata.get("converted_to_remision_id") or "").strip()
        if remision_id:
            return {"id": remision_id}
        remision_folio = str(metadata.get("remision_folio") or metadata.get("converted_to_remision_folio") or "").strip()
        if remision_folio:
            return {"folio": remision_folio}
        return None

    def _blank(self, value):
        value = str(value or "").strip()
        return value or None
