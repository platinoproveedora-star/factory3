from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _shared import VALID_TRIP_STATUS, computed_status, db, is_dry_run, now_iso, resolve_context, table_filters


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
            return {"ok": True, "message": "dry_run: no se actualizo viaje", "data": {"trip": {**current, **update}}}
        result = db(ctx).rest_update("logistics_trips", update, table_filters(ctx, {"id": f"eq.{trip_id}"}))
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
