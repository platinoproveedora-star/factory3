from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from factory.engine import SupabaseClient


def _text(value: object) -> str:
    return str(value or "").strip()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_local_time(value: str) -> tuple[int, int]:
    parts = value.strip().split(":")
    if len(parts) != 2:
        raise ValueError("local_time debe ser HH:MM")
    hour, minute = int(parts[0]), int(parts[1])
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        raise ValueError("local_time debe ser HH:MM valido")
    return hour, minute


def _next_run_at(schedule_type: str, local_time: str, tz_name: str, interval_minutes: int | None) -> str:
    now = _utc_now()
    if schedule_type == "hourly":
        return (now + timedelta(hours=1)).isoformat()
    if schedule_type == "interval_minutes":
        minutes = int(interval_minutes or 0)
        if minutes <= 0:
            raise ValueError("interval_minutes debe ser mayor a 0")
        return (now + timedelta(minutes=minutes)).isoformat()
    hour, minute = _parse_local_time(local_time)
    tz = ZoneInfo(tz_name)
    local_now = now.astimezone(tz)
    candidate = local_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= local_now:
        candidate += timedelta(days=1)
    return candidate.astimezone(timezone.utc).isoformat()


class FactoryScheduleUpsertService:
    def ejecutar(self, context: dict) -> dict:
        schedule_name = _text(context.get("schedule_name"))
        skill_name = _text(context.get("skill_name"))
        if not schedule_name:
            return {"ok": False, "error": "schedule_name requerido"}
        if not skill_name:
            return {"ok": False, "error": "skill_name requerido"}

        schema = _text(context.get("scheduler_schema") or context.get("schema") or "public")
        schedule_type = _text(context.get("schedule_type") or "daily")
        tz_name = _text(context.get("timezone") or "America/Mexico_City")
        local_time = _text(context.get("local_time") or "")
        interval_minutes = context.get("interval_minutes")
        if schedule_type == "daily" and not local_time:
            return {"ok": False, "error": "local_time requerido para schedule_type=daily"}
        try:
            next_run_at = _text(context.get("next_run_at")) or _next_run_at(schedule_type, local_time, tz_name, int(interval_minutes) if interval_minutes else None)
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

        row = {
            "schedule_name": schedule_name,
            "empresa_id": context.get("empresa_id") or context.get("company_id"),
            "project_code": context.get("project_code"),
            "module_code": context.get("module_code"),
            "skill_name": skill_name,
            "skill_source": _text(context.get("skill_source") or "internos"),
            "context": context.get("skill_context") if isinstance(context.get("skill_context"), dict) else context.get("context", {}),
            "timezone": tz_name,
            "schedule_type": schedule_type,
            "local_time": local_time or None,
            "interval_minutes": int(interval_minutes) if interval_minutes else None,
            "status": _text(context.get("status") or "active"),
            "next_run_at": next_run_at,
            "metadata": context.get("metadata") if isinstance(context.get("metadata"), dict) else {},
        }

        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run", "data": {"schedule": row}}

        db = SupabaseClient({"schema": schema})
        existing = db.rest_select("factory_schedules", filters={"schedule_name": f"eq.{schedule_name}"}, select="id,folio", limit=1)
        if not existing.get("ok"):
            return existing
        rows = existing.get("data") or []
        if rows:
            result = db.rest_update("factory_schedules", {**row, "updated_at": _utc_now().isoformat()}, {"id": f"eq.{rows[0]['id']}"})
            if not result.get("ok"):
                return result
            data = result.get("data") or []
            return {"ok": True, "data": {"schedule": data[0] if isinstance(data, list) and data else data, "updated": True}}

        row["folio"] = self._next_folio(db)
        result = db.rest_insert("factory_schedules", row)
        if not result.get("ok"):
            return result
        data = result.get("data") or []
        return {"ok": True, "data": {"schedule": data[0] if isinstance(data, list) and data else data, "created": True}}

    def _next_folio(self, db: SupabaseClient) -> str:
        result = db.rest_select("factory_schedules", select="folio", order="folio.desc", limit=1)
        rows = result.get("data") or [] if result.get("ok") else []
        if not rows:
            return "FSCH-00001"
        try:
            num = int(str(rows[0].get("folio", "FSCH-00000")).split("-")[-1]) + 1
        except Exception:
            num = 1
        return f"FSCH-{num:05d}"
