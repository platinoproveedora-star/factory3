from __future__ import annotations

import re

from factory.engine import SupabaseClient

_SCHEMA = "fleet4all"
_FOLIO_PREFIX = "CP-"
_REQUIRED_MERCANCIA_FIELDS = ("descripcion", "cantidad", "peso_kg", "clave_prod_serv")


class CartaporteBuildService:
    def ejecutar(self, context: dict) -> dict:
        empresa_id = str(context.get("empresa_id") or "").strip()
        trip_folio = str(context.get("trip_folio") or "").strip()
        cfdi_type = str(context.get("cfdi_type") or "traslado").strip().lower()
        if not empresa_id or not trip_folio:
            return {"ok": False, "error": "missing_fields", "data": {"missing": ["empresa_id", "trip_folio"]}}
        if cfdi_type not in ("traslado", "ingreso"):
            return {"ok": False, "error": "invalid_cartaporte", "data": {"detail": "cfdi_type debe ser traslado o ingreso"}}

        db = SupabaseClient({**context, "schema": _SCHEMA})

        trip_res = db.rest_select("trips", filters={"empresa_id": f"eq.{empresa_id}", "trip_folio": f"eq.{trip_folio}"}, select="*", limit=1)
        if not trip_res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": trip_res.get("error")}}
        trips = trip_res.get("data") or []
        if not trips:
            return {"ok": False, "error": "missing_fields", "data": {"missing": ["trip"]}}
        trip = trips[0]

        missing: list[str] = []
        unit = None
        if trip.get("unit_key"):
            unit_res = db.rest_select("units", filters={"empresa_id": f"eq.{empresa_id}", "unit_key": f"eq.{trip['unit_key']}"}, select="*", limit=1)
            if not unit_res.get("ok"):
                return {"ok": False, "error": "db_persistence_failed", "data": {"detail": unit_res.get("error")}}
            unit = (unit_res.get("data") or [None])[0]
        if not unit or not unit.get("plate"):
            missing.append("unit_plate")

        driver = None
        if trip.get("driver_key"):
            driver_res = db.rest_select("drivers", filters={"empresa_id": f"eq.{empresa_id}", "driver_key": f"eq.{trip['driver_key']}"}, select="*", limit=1)
            if not driver_res.get("ok"):
                return {"ok": False, "error": "db_persistence_failed", "data": {"detail": driver_res.get("error")}}
            driver = (driver_res.get("data") or [None])[0]
        if not driver or not driver.get("license_number"):
            missing.append("driver_license")

        if not trip.get("origin"):
            missing.append("origin")
        if not trip.get("destination"):
            missing.append("destination")

        mercancias = context.get("mercancias") if isinstance(context.get("mercancias"), list) else []
        if not mercancias:
            missing.append("mercancias")
        else:
            for idx, m in enumerate(mercancias):
                for field in _REQUIRED_MERCANCIA_FIELDS:
                    if not m.get(field):
                        missing.append(f"mercancias[{idx}].{field}")

        if missing:
            return {"ok": False, "error": "missing_fields", "data": {"missing": missing}}

        # "cartaporte_stamps" (segun 02_SCHEMA_FLEET4ALL.sql) solo guarda folio/status/resultado del
        # timbrado; los datos derivados (mercancias, vehiculo, operador) viajan en la respuesta y el
        # caller los reenvia a cartaporte_validate/pac_stamp — la tabla no tiene columnas para ellos.
        draft = {
            "empresa_id": empresa_id,
            "trip_folio": trip_folio,
            "cfdi_type": cfdi_type,
            "origin": trip.get("origin"),
            "destination": trip.get("destination"),
            "unit_plate": unit.get("plate"),
            "unit_type": unit.get("unit_type"),
            "unit_year": unit.get("year"),
            "driver_name": driver.get("full_name"),
            "driver_license": driver.get("license_number"),
            "mercancias": mercancias,
            "extra": context.get("extra") or {},
            "uuid_sat": None,
            "xml_path": None,
            "pdf_path": None,
            "pac_provider": None,
            "stamp_status": "draft",
            "error_detail": None,
        }

        if context.get("dry_run", True):
            return {
                "ok": True,
                "message": "dry_run: no se escribio en fleet4all.cartaporte_stamps",
                "data": {"cartaporte": {**draft, "stamp_folio": None}, "warnings": ["dry_run: folio no asignado"]},
            }

        folio = self._next_folio(db, empresa_id)
        persist_row = {
            "empresa_id": empresa_id, "stamp_folio": folio, "trip_folio": trip_folio, "cfdi_type": cfdi_type,
            "uuid_sat": None, "xml_path": None, "pdf_path": None, "pac_provider": None,
            "stamp_status": "draft", "error_detail": None,
        }
        res = db.rest_insert("cartaporte_stamps", persist_row)
        if not res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": res.get("error")}}
        persisted_meta = (res.get("data") or [persist_row])[0]
        full_draft = {**draft, **persisted_meta}
        return {"ok": True, "data": {"cartaporte": full_draft, "warnings": []}}

    def _next_folio(self, db: SupabaseClient, empresa_id: str) -> str:
        res = db.rest_select(
            "cartaporte_stamps",
            filters={"empresa_id": f"eq.{empresa_id}", "stamp_folio": f"like.{_FOLIO_PREFIX}*"},
            select="stamp_folio",
            order="stamp_folio.desc",
            limit=1,
        )
        rows = (res.get("data") or []) if res.get("ok") else []
        last_n = 0
        if rows:
            match = re.search(r"(\d+)$", str(rows[0].get("stamp_folio") or ""))
            if match:
                last_n = int(match.group(1))
        return f"{_FOLIO_PREFIX}{last_n + 1:04d}"
