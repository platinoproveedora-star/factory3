"""Service for ig_best_time_selector - returns optimal Instagram posting times by format and region."""
from __future__ import annotations

_VALID_FORMATS = {"reel", "carousel", "post", "story"}
_VALID_REGIONS = {"latam", "us", "europe", "global"}

_BEST_TIMES: dict[str, dict[str, list[tuple[str, str]]]] = {
    "reel": {
        "latam": [("Thursday","09:00"),("Wednesday","12:00"),("Tuesday","09:00"),("Friday","18:00"),("Monday","09:00"),("Saturday","11:00"),("Sunday","20:00")],
        "us":    [("Wednesday","11:00"),("Thursday","10:00"),("Tuesday","14:00"),("Friday","09:00"),("Monday","10:00"),("Saturday","10:00"),("Sunday","19:00")],
        "europe":[("Wednesday","12:00"),("Thursday","12:00"),("Tuesday","12:00"),("Friday","10:00"),("Monday","12:00"),("Saturday","11:00"),("Sunday","18:00")],
    },
    "carousel": {
        "latam": [("Wednesday","12:00"),("Thursday","09:00"),("Friday","11:00"),("Tuesday","12:00"),("Monday","10:00"),("Saturday","10:00"),("Sunday","19:00")],
        "us":    [("Wednesday","12:00"),("Thursday","09:00"),("Friday","11:00"),("Tuesday","10:00"),("Monday","11:00"),("Saturday","11:00"),("Sunday","18:00")],
        "europe":[("Wednesday","13:00"),("Thursday","13:00"),("Friday","12:00"),("Tuesday","12:00"),("Monday","12:00"),("Saturday","12:00"),("Sunday","17:00")],
    },
    "post": {
        "latam": [("Wednesday","12:00"),("Thursday","09:00"),("Friday","11:00"),("Tuesday","12:00"),("Monday","10:00"),("Saturday","10:00"),("Sunday","19:00")],
        "us":    [("Wednesday","11:00"),("Thursday","09:00"),("Friday","11:00"),("Tuesday","10:00"),("Monday","09:00"),("Saturday","11:00"),("Sunday","19:00")],
        "europe":[("Wednesday","12:00"),("Thursday","12:00"),("Friday","11:00"),("Tuesday","12:00"),("Monday","12:00"),("Saturday","11:00"),("Sunday","17:00")],
    },
    "story": {
        "latam": [("Monday","09:00"),("Wednesday","09:00"),("Friday","09:00"),("Tuesday","08:00"),("Thursday","08:00"),("Saturday","10:00"),("Sunday","18:00")],
        "us":    [("Monday","08:00"),("Wednesday","08:00"),("Friday","08:00"),("Tuesday","08:00"),("Thursday","08:00"),("Saturday","09:00"),("Sunday","17:00")],
        "europe":[("Monday","09:00"),("Wednesday","09:00"),("Friday","09:00"),("Tuesday","09:00"),("Thursday","09:00"),("Saturday","10:00"),("Sunday","18:00")],
    },
}


class IgBestTimeSelectorService:

    def ejecutar(self, context: dict) -> dict:
        valido, error = self._validar(context)
        if not valido:
            return {"ok": False, "error": error}
        if context.get("dry_run", False):
            return {"ok": True, "message": "dry_run", "data": context}
        return self._ejecutar(context)

    def _validar(self, context: dict) -> tuple[bool, str | None]:
        fmt = context.get("format")
        if not fmt:
            return False, "format es requerido"
        if fmt not in _VALID_FORMATS:
            return False, f"format debe ser uno de: {', '.join(sorted(_VALID_FORMATS))}"
        region = context.get("audience_region")
        if region is not None and region not in _VALID_REGIONS:
            return False, f"audience_region debe ser uno de: {', '.join(sorted(_VALID_REGIONS))}"
        count = context.get("count")
        if count is not None and (not isinstance(count, int) or count < 1 or count > 7):
            return False, "count debe ser un entero entre 1 y 7"
        return True, None

    def _ejecutar(self, context: dict) -> dict:
        fmt = context["format"]
        region = context.get("audience_region", "latam")
        count = context.get("count", 3)

        lookup_region = "latam" if region == "global" else region
        slots_raw = _BEST_TIMES[fmt][lookup_region][:count]
        best_slots = [{"day": day, "time": time, "rank": i + 1} for i, (day, time) in enumerate(slots_raw)]

        return {
            "ok": True,
            "data": {
                "format": fmt,
                "audience_region": region,
                "best_slots": best_slots,
                "note": (
                    "Los horarios son locales a la region de audiencia. "
                    "Las primeras 24-48h de engagement son criticas para el algoritmo."
                ),
            },
        }
