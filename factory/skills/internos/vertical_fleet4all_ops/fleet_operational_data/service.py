from __future__ import annotations

from datetime import date, timedelta

from factory.engine import SupabaseClient

_DEFAULT_SCHEMA = "fleet4all"
_DEFAULT_LIMIT = 60
_MAX_LIMIT = 200

_SECTIONS = {
    "trips",
    "drivers",
    "units",
    "receivables",
    "payments",
    "rates",
    "quotes",
    "fuel_loads",
    "fuel_efficiency",
    "parts",
    "maintenance_plans",
    "services",
    "cartaporte_stamps",
    "settlements",
}

_MONTH_NAMES = (
    "Enero",
    "Febrero",
    "Marzo",
    "Abril",
    "Mayo",
    "Junio",
    "Julio",
    "Agosto",
    "Septiembre",
    "Octubre",
    "Noviembre",
    "Diciembre",
)


class FleetOperationalDataService:
    def ejecutar(self, context: dict) -> dict:
        empresa_id = str(context.get("empresa_id") or context.get("company_id") or "").strip()
        if not empresa_id:
            return {"ok": False, "error": "empresa_id_requerido"}

        requested = context.get("sections") or context.get("include") or ["trips", "drivers", "units"]
        if isinstance(requested, str):
            requested = [item.strip() for item in requested.split(",") if item.strip()]
        sections = [section for section in requested if section in _SECTIONS]
        if not sections:
            return {"ok": False, "error": "sections_requerido"}

        db = SupabaseClient({**context, "schema": context.get("schema") or _DEFAULT_SCHEMA})
        period = self._period(context)
        limit = min(max(int(context.get("limit") or _DEFAULT_LIMIT), 1), _MAX_LIMIT)
        data: dict = {"empresa_id": empresa_id, "period": period}
        warnings: list[str] = []

        loaders = {
            "trips": lambda: self._trips(db, empresa_id, limit),
            "drivers": lambda: self._simple(db, "drivers", empresa_id, "driver_key,full_name,phone,license_number,pay_scheme,pay_rate,status", "full_name.asc", limit),
            "units": lambda: self._simple(db, "units", empresa_id, "unit_key,plate,brand,model,year,unit_type,odometer_km,status", "unit_key.asc", limit),
            "receivables": lambda: self._receivables(db, empresa_id, limit),
            "payments": lambda: self._simple(db, "payments", empresa_id, "payment_folio,trip_folio,customer,payment_date,amount,currency,method,tracking_key,notes,status,created_at", "payment_date.desc", limit),
            "rates": lambda: self._simple(db, "rates", empresa_id, "rate_key,origin,destination,cargo_type,base_price,price_per_km,price_per_ton,currency,status", "origin.asc", limit),
            "quotes": lambda: self._simple(db, "quotes", empresa_id, "quote_folio,customer,origin,destination,cargo_type,quoted_price,currency,valid_until,status,trip_folio,created_at", "created_at.desc", limit),
            "fuel_loads": lambda: self._simple(db, "fuel_loads", empresa_id, "fuel_folio,unit_key,driver_key,trip_folio,load_date,liters,amount,currency,price_per_liter,odometer_km,station", "load_date.desc", limit),
            "fuel_efficiency": lambda: self._simple(db, "fuel_efficiency", empresa_id, "unit_key,period_from,period_to,km_per_liter,expected_km_per_liter,deviation_pct,flag", "period_to.desc", limit),
            "parts": lambda: self._simple(db, "parts", empresa_id, "part_key,name,unit_measure,stock,min_stock,avg_cost,currency", "part_key.asc", limit),
            "maintenance_plans": lambda: self._simple(db, "maintenance_plans", empresa_id, "plan_folio,unit_key,service_type,every_km,every_days,last_service_km,last_service_date,next_due_km,next_due_date,status", "next_due_date.asc", limit),
            "services": lambda: self._simple(db, "services", empresa_id, "service_folio,unit_key,plan_folio,service_date,odometer_km,service_type,description,cost,currency,workshop", "service_date.desc", limit),
            "cartaporte_stamps": lambda: self._simple(db, "cartaporte_stamps", empresa_id, "stamp_folio,trip_folio,cfdi_type,uuid_sat,pac_provider,stamp_status,error_detail,stamped_at,created_at", "created_at.desc", limit),
            "settlements": lambda: self._simple(db, "settlements", empresa_id, "settlement_folio,driver_key,period_from,period_to,gross_amount,advances_deducted,other_deductions,net_amount,currency,status,created_at", "created_at.desc", limit),
        }

        for section in sections:
            result = loaders[section]()
            if not result.get("ok"):
                warnings.append(f"{section}: {result.get('error')}")
                data[section] = []
            else:
                data[section] = result.get("data") or []
                if section == "trips":
                    data["trip_months"] = self._trip_months(data[section])

        if "maintenance_plans" in data and "units" in data:
            data["maintenance_due_soon"] = self._due_soon(data["maintenance_plans"], data["units"])

        return {"ok": True, "data": {**data, "warnings": warnings}}

    def _period(self, context: dict) -> dict:
        raw = context.get("period") if isinstance(context.get("period"), dict) else {}
        if raw.get("from") or raw.get("to"):
            return {"from": raw.get("from"), "to": raw.get("to")}
        today = date.today()
        return {"from": (today - timedelta(days=30)).isoformat(), "to": today.isoformat()}

    def _simple(self, db: SupabaseClient, table: str, empresa_id: str, select: str, order: str, limit: int) -> dict:
        res = db.rest_select(table, filters={"empresa_id": f"eq.{empresa_id}"}, select=select, order=order, limit=limit)
        if not res.get("ok"):
            return {"ok": False, "error": res.get("error")}
        return {"ok": True, "data": res.get("data") or []}

    def _trips(self, db: SupabaseClient, empresa_id: str, limit: int) -> dict:
        res = db.rest_select(
            "trips",
            filters={"empresa_id": f"eq.{empresa_id}"},
            select="trip_folio,customer,origin,destination,departure_date,arrival_date,sale_price,trip_cost,trip_profit,currency,driver_key,unit_key,distance_km,trip_status,payment_status",
            order="departure_date.desc",
            limit=limit,
        )
        if not res.get("ok"):
            return {"ok": False, "error": res.get("error")}
        trips = res.get("data") or []
        if not trips:
            return {"ok": True, "data": []}

        folios = [str(trip.get("trip_folio") or "").strip() for trip in trips if trip.get("trip_folio")]
        expenses_by_trip = {folio: 0.0 for folio in folios}
        if folios:
            expenses_res = db.rest_select(
                "expenses",
                filters={"empresa_id": f"eq.{empresa_id}", "trip_folio": f"in.({','.join(folios)})"},
                select="trip_folio,amount",
            )
            if not expenses_res.get("ok"):
                return {"ok": False, "error": expenses_res.get("error")}
            for expense in expenses_res.get("data") or []:
                folio = str(expense.get("trip_folio") or "").strip()
                expenses_by_trip[folio] = expenses_by_trip.get(folio, 0.0) + float(expense.get("amount") or 0)

        enriched = []
        for trip in trips:
            expenses_total = round(expenses_by_trip.get(str(trip.get("trip_folio") or ""), 0.0), 2)
            sale_price = float(trip.get("sale_price") or 0)
            live_profit = round(sale_price - expenses_total, 2)
            enriched.append({
                **trip,
                "expenses_total": expenses_total,
                "live_trip_cost": expenses_total,
                "live_trip_profit": live_profit,
                "trip_cost": expenses_total,
                "trip_profit": live_profit,
            })
        return {"ok": True, "data": enriched}

    def _trip_months(self, trips: list[dict]) -> list[dict]:
        today = date.today()
        months = [self._month_window(today, offset) for offset in range(3)]
        result = []
        for month in months:
            rows = [trip for trip in trips if self._trip_in_month(trip, month["key"])]
            sale_total = round(sum(float(trip.get("sale_price") or 0) for trip in rows), 2)
            expense_total = round(sum(float(trip.get("expenses_total") or trip.get("trip_cost") or 0) for trip in rows), 2)
            profit_total = round(sum(float(trip.get("live_trip_profit") or trip.get("trip_profit") or 0) for trip in rows), 2)
            result.append(
                {
                    **month,
                    "trips": rows,
                    "totals": {
                        "count": len(rows),
                        "sale_price": sale_total,
                        "expenses": expense_total,
                        "profit": profit_total,
                    },
                }
            )
        return result

    def _month_window(self, today: date, offset: int) -> dict:
        year = today.year
        month = today.month - offset
        while month <= 0:
            month += 12
            year -= 1
        start = date(year, month, 1)
        if month == 12:
            end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end = date(year, month + 1, 1) - timedelta(days=1)
        label = f"{_MONTH_NAMES[start.month - 1]} {start.year}"
        return {
            "key": start.strftime("%Y-%m"),
            "label": label,
            "from": start.isoformat(),
            "to": end.isoformat(),
            "offset": offset,
        }

    def _trip_in_month(self, trip: dict, month_key: str) -> bool:
        raw_date = str(trip.get("departure_date") or trip.get("arrival_date") or "").strip()
        return raw_date.startswith(month_key)

    def _receivables(self, db: SupabaseClient, empresa_id: str, limit: int) -> dict:
        res = db.rest_select(
            "receivables",
            filters={"empresa_id": f"eq.{empresa_id}"},
            select="receivable_folio,trip_folio,customer,total_amount,paid_amount,balance,currency,trip_date,due_date,collection_status",
            order="due_date.asc",
            limit=limit,
        )
        if not res.get("ok"):
            return {"ok": False, "error": res.get("error")}
        return {"ok": True, "data": res.get("data") or []}

    def _due_soon(self, plans: list[dict], units: list[dict]) -> list[dict]:
        today = date.today()
        odometer_by_unit = {unit.get("unit_key"): float(unit.get("odometer_km") or 0) for unit in units}
        rows = []
        for plan in plans:
            odometer = odometer_by_unit.get(plan.get("unit_key"))
            km_remaining = (
                float(plan.get("next_due_km")) - odometer
                if plan.get("next_due_km") is not None and odometer is not None
                else None
            )
            days_remaining = None
            if plan.get("next_due_date"):
                try:
                    days_remaining = (date.fromisoformat(str(plan["next_due_date"])) - today).days
                except ValueError:
                    days_remaining = None
            if (
                km_remaining is not None and km_remaining <= 1000
            ) or (
                days_remaining is not None and days_remaining <= 15
            ):
                rows.append({**plan, "km_remaining": km_remaining, "days_remaining": days_remaining})
        return rows
