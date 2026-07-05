from __future__ import annotations

import re

from factory.engine import SupabaseClient

_SCHEMA = "fleet4all"
_FOLIO_PREFIX = "MV-"


class PartsKardexService:
    def ejecutar(self, context: dict) -> dict:
        empresa_id = str(context.get("empresa_id") or "").strip()
        if not empresa_id:
            return {"ok": False, "error": "empresa_id_requerido"}

        action = str(context.get("action") or "movement").strip().lower()
        if action == "part_upsert":
            return self._part_upsert(context, empresa_id)
        return self._movement(context, empresa_id)

    def _part_upsert(self, context: dict, empresa_id: str) -> dict:
        part_key = str(context.get("part_key") or "").strip()
        name = str(context.get("name") or "").strip()
        if not part_key or not name:
            return {"ok": False, "error": "missing_required_fields"}

        base = {
            "empresa_id": empresa_id,
            "part_key": part_key,
            "name": name,
            "unit_measure": str(context.get("unit_measure") or "pza"),
            "min_stock": self._to_amount(context.get("min_stock")) or 0.0,
            "currency": str(context.get("currency") or "MXN").strip().upper(),
        }

        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run: no se escribio en fleet4all.parts", "data": {"part": base, "warnings": []}}

        db = SupabaseClient({**context, "schema": _SCHEMA})
        existing_res = db.rest_select("parts", filters={"empresa_id": f"eq.{empresa_id}", "part_key": f"eq.{part_key}"}, select="*", limit=1)
        if not existing_res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": existing_res.get("error")}}
        existing = (existing_res.get("data") or [None])[0]

        if existing:
            upd = db.rest_update(
                "parts",
                values={"name": name, "unit_measure": base["unit_measure"], "min_stock": base["min_stock"], "currency": base["currency"]},
                filters={"empresa_id": f"eq.{empresa_id}", "part_key": f"eq.{part_key}"},
            )
            if not upd.get("ok"):
                return {"ok": False, "error": "db_persistence_failed", "data": {"detail": upd.get("error")}}
            persisted = (upd.get("data") or [base])[0]
        else:
            ins = db.rest_insert("parts", {**base, "stock": 0.0, "avg_cost": 0.0})
            if not ins.get("ok"):
                return {"ok": False, "error": "db_persistence_failed", "data": {"detail": ins.get("error")}}
            persisted = (ins.get("data") or [base])[0]

        return {"ok": True, "data": {"part": persisted, "warnings": []}}

    def _movement(self, context: dict, empresa_id: str) -> dict:
        part_key = str(context.get("part_key") or "").strip()
        movement_type = str(context.get("movement_type") or "").strip().lower()
        if not part_key or movement_type not in ("in", "out"):
            return {"ok": False, "error": "missing_required_fields"}

        quantity = self._to_amount(context.get("quantity"))
        if quantity is None or quantity <= 0:
            return {"ok": False, "error": "invalid_amount"}

        db = SupabaseClient({**context, "schema": _SCHEMA})
        part_res = db.rest_select("parts", filters={"empresa_id": f"eq.{empresa_id}", "part_key": f"eq.{part_key}"}, select="*", limit=1)
        if not part_res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": part_res.get("error")}}
        parts = part_res.get("data") or []
        if not parts:
            return {"ok": False, "error": "part_not_found"}
        part = parts[0]
        stock = float(part.get("stock") or 0)
        avg_cost = float(part.get("avg_cost") or 0)

        if movement_type == "out" and quantity > stock:
            return {"ok": False, "error": "insufficient_stock"}

        unit_cost = self._to_amount(context.get("unit_cost"))
        if movement_type == "in":
            new_stock = stock + quantity
            new_avg_cost = (
                round(((stock * avg_cost) + (quantity * unit_cost)) / new_stock, 4)
                if unit_cost is not None and new_stock > 0
                else avg_cost
            )
        else:
            new_stock = stock - quantity
            new_avg_cost = avg_cost

        base = {
            "empresa_id": empresa_id,
            "part_key": part_key,
            "movement_type": movement_type,
            "quantity": quantity,
            "service_folio": context.get("service_folio"),
            "unit_key": context.get("unit_key"),
            "movement_date": context.get("movement_date"),
            "notes": context.get("notes"),
        }

        warnings: list[str] = []
        min_stock = float(part.get("min_stock") or 0)
        if new_stock < min_stock:
            warnings.append("below_min_stock")

        if context.get("dry_run", True):
            return {
                "ok": True,
                "message": "dry_run: no se persistio",
                "data": {
                    "movement": {**base, "movement_folio": None, "projected_stock": new_stock, "projected_avg_cost": new_avg_cost},
                    "warnings": warnings + ["dry_run: no se persistio"],
                },
            }

        folio = self._next_folio(db, empresa_id)
        row = {**base, "movement_folio": folio}
        res = db.rest_insert("part_movements", row)
        if not res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": res.get("error")}}
        created = (res.get("data") or [row])[0]

        part_upd = db.rest_update(
            "parts", values={"stock": new_stock, "avg_cost": new_avg_cost},
            filters={"empresa_id": f"eq.{empresa_id}", "part_key": f"eq.{part_key}"},
        )
        if not part_upd.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": part_upd.get("error")}}

        return {"ok": True, "data": {"movement": created, "warnings": warnings}}

    def _to_amount(self, value) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _next_folio(self, db: SupabaseClient, empresa_id: str) -> str:
        res = db.rest_select(
            "part_movements",
            filters={"empresa_id": f"eq.{empresa_id}", "movement_folio": f"like.{_FOLIO_PREFIX}*"},
            select="movement_folio",
            order="movement_folio.desc",
            limit=1,
        )
        rows = (res.get("data") or []) if res.get("ok") else []
        last_n = 0
        if rows:
            match = re.search(r"(\d+)$", str(rows[0].get("movement_folio") or ""))
            if match:
                last_n = int(match.group(1))
        return f"{_FOLIO_PREFIX}{last_n + 1:04d}"
