from __future__ import annotations

import random
import time

from factory.engine import SupabaseClient

_SCHEMA = "factu4all"
_FIELDS = ["is_default", "status", "pac_provider"]


class FolioSeriesManageService:
    def ejecutar(self, context: dict) -> dict:
        company_id = str(context.get("company_id") or context.get("empresa_id") or "").strip()
        if not company_id:
            return {"ok": False, "error": "company_id_requerido"}

        action = str(context.get("action") or "list").strip().lower()
        db = SupabaseClient({**context, "schema": _SCHEMA})

        if action == "list":
            return self._list(db, company_id)
        if action == "next":
            return self._next(db, context, company_id)

        cfdi_type = str(context.get("cfdi_type") or "").strip().lower()
        series = str(context.get("series") or "").strip().upper()
        environment = str(context.get("environment") or "sandbox").strip().lower()
        if not cfdi_type or not series:
            return {"ok": False, "error": "cfdi_type_y_series_requeridos"}

        values = {key: context[key] for key in _FIELDS if key in context}

        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run: no se escribio en folio_series", "data": {"company_id": company_id, "series": series, "cfdi_type": cfdi_type, "environment": environment, **values}}

        filters = {"company_id": f"eq.{company_id}", "series": f"eq.{series}", "cfdi_type": f"eq.{cfdi_type}", "environment": f"eq.{environment}"}
        existing = db.rest_select("folio_series", filters=filters, select="id", limit=1)
        if not existing.get("ok"):
            return {"ok": False, "error": "db_query_failed", "data": {"detail": existing.get("error")}}

        if existing.get("data"):
            res = db.rest_update("folio_series", values, filters)
        else:
            row = {
                "folio": f"FS-{company_id}-{series}-{cfdi_type}-{environment}",
                "company_id": company_id,
                "series": series,
                "cfdi_type": cfdi_type,
                "environment": environment,
                "current_number": 0,
                "next_number": 1,
                "status": values.get("status") or "active",
                **{key: value for key, value in values.items() if key != "status"},
            }
            res = db.rest_insert("folio_series", row)

        if not res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": res.get("error")}}
        return {"ok": True, "data": {"folio_series": (res.get("data") or [{}])[0]}}

    def _list(self, db: SupabaseClient, company_id: str) -> dict:
        res = db.rest_select("folio_series", filters={"company_id": f"eq.{company_id}"}, select="*", order="series.asc")
        if not res.get("ok"):
            return {"ok": False, "error": "db_query_failed", "data": {"detail": res.get("error")}}
        return {"ok": True, "data": {"folio_series": res.get("data") or []}}

    def _next(self, db: SupabaseClient, context: dict, company_id: str) -> dict:
        cfdi_type = str(context.get("cfdi_type") or "").strip().lower()
        series = str(context.get("series") or "").strip().upper()
        environment = str(context.get("environment") or "sandbox").strip().lower()
        base_filters = {"company_id": f"eq.{company_id}", "cfdi_type": f"eq.{cfdi_type}", "environment": f"eq.{environment}"}
        if series:
            base_filters["series"] = f"eq.{series}"
        else:
            base_filters["is_default"] = "eq.true"

        dry_run = context.get("dry_run", True)

        # Compare-and-swap: el UPDATE solo aplica si next_number sigue igual a
        # lo que leimos. Si 0 filas cambian, otro request ya reservo ese
        # numero primero — se reintenta leyendo el valor fresco.
        for attempt in range(12):
            if attempt > 0:
                time.sleep(random.uniform(0.02, 0.08) * attempt)
            rows_res = db.rest_select("folio_series", filters=base_filters, select="*", limit=1)
            if not rows_res.get("ok"):
                return {"ok": False, "error": "db_query_failed", "data": {"detail": rows_res.get("error")}}
            rows = rows_res.get("data") or []
            if not rows:
                return {"ok": False, "error": "folio_series_not_found"}
            current = rows[0]
            number = int(current.get("next_number") or 1)
            cfdi_folio = f"{current['series']}{number:04d}"

            if dry_run:
                return {"ok": True, "message": "dry_run: numero no reservado", "data": {"series": current["series"], "number": number, "cfdi_folio": cfdi_folio}}

            cas_filters = {
                "id": f"eq.{current['id']}",
                "next_number": f"eq.{number}",
            }
            upd = db.rest_update("folio_series", {"current_number": number, "next_number": number + 1}, cas_filters)
            if not upd.get("ok"):
                return {"ok": False, "error": "db_persistence_failed", "data": {"detail": upd.get("error")}}
            if upd.get("data"):
                return {"ok": True, "data": {"series": current["series"], "number": number, "cfdi_folio": cfdi_folio, "folio_series_id": current["id"]}}
            # otro request se adelanto — reintentar con el valor fresco

        return {"ok": False, "error": "folio_reservation_conflict", "data": {"detail": "No se pudo reservar el folio tras varios intentos, hay demasiada concurrencia"}}
