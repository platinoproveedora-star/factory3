from __future__ import annotations

import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from factory.engine import SkillLoader, SkillRunner, SupabaseClient


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_dt(value: str) -> datetime:
    text = str(value or "").replace("Z", "+00:00")
    dt = datetime.fromisoformat(text)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _next_after(schedule: dict, base: datetime) -> str | None:
    schedule_type = str(schedule.get("schedule_type") or "daily")
    if schedule_type == "once":
        return None
    if schedule_type == "hourly":
        return (base + timedelta(hours=1)).isoformat()
    if schedule_type == "interval_minutes":
        return (base + timedelta(minutes=int(schedule.get("interval_minutes") or 1))).isoformat()
    tz = ZoneInfo(str(schedule.get("timezone") or "America/Mexico_City"))
    local_time = str(schedule.get("local_time") or "19:00")
    hour, minute = [int(part) for part in local_time.split(":", 1)]
    local_base = base.astimezone(tz)
    candidate = local_base.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= local_base:
        candidate += timedelta(days=1)
    return candidate.astimezone(timezone.utc).isoformat()


def _parse_hhmm(value: str) -> tuple[int, int]:
    hour, minute = [int(part) for part in str(value or "").split(":", 1)]
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        raise ValueError("hora invalida")
    return hour, minute


def _active_window(schedule: dict) -> dict:
    metadata = schedule.get("metadata") if isinstance(schedule.get("metadata"), dict) else {}
    window = metadata.get("active_window") if isinstance(metadata.get("active_window"), dict) else {}
    if not window:
        return {}
    start = str(window.get("start") or "").strip()
    end = str(window.get("end") or "").strip()
    if not start or not end:
        return {}
    return {
        "start": start,
        "end": end,
        "timezone": str(window.get("timezone") or schedule.get("timezone") or "America/Mexico_City"),
    }


def _is_inside_window(schedule: dict, now: datetime) -> bool:
    window = _active_window(schedule)
    if not window:
        return True
    local_now = now.astimezone(ZoneInfo(window["timezone"]))
    start_hour, start_minute = _parse_hhmm(window["start"])
    end_hour, end_minute = _parse_hhmm(window["end"])
    start = local_now.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
    end = local_now.replace(hour=end_hour, minute=end_minute, second=0, microsecond=0)
    if start <= end:
        return start <= local_now <= end
    return local_now >= start or local_now <= end


def _next_window_start(schedule: dict, now: datetime) -> str:
    window = _active_window(schedule)
    if not window:
        next_run_at = _next_after(schedule, now)
        return next_run_at or now.isoformat()
    local_now = now.astimezone(ZoneInfo(window["timezone"]))
    start_hour, start_minute = _parse_hhmm(window["start"])
    candidate = local_now.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
    if candidate <= local_now:
        candidate += timedelta(days=1)
    return candidate.astimezone(timezone.utc).isoformat()


class FactoryScheduleRunnerService:
    def ejecutar(self, context: dict) -> dict:
        schema = str(context.get("scheduler_schema") or context.get("schema") or "public").strip()
        now = _parse_dt(str(context.get("now") or _utc_now().isoformat()))
        limit = int(context.get("limit") or 20)
        dry_run = bool(context.get("dry_run", True))

        db = SupabaseClient({"schema": schema})
        result = db.rest_select(
            "factory_schedules",
            filters={"status": "eq.active", "next_run_at": f"lte.{now.isoformat()}"},
            select="*",
            order="next_run_at.asc",
            limit=limit,
        )
        if not result.get("ok"):
            return result
        schedules = result.get("data") or []
        if dry_run:
            return {"ok": True, "message": "dry_run", "data": {"due": schedules, "count": len(schedules)}}

        runner = self._runner()
        processed = []
        for schedule in schedules:
            skill_name = schedule.get("skill_name")
            source = schedule.get("skill_source") or "internos"
            skill_context = schedule.get("context") if isinstance(schedule.get("context"), dict) else {}
            if not _is_inside_window(schedule, now):
                next_run_at = _next_window_start(schedule, now)
                db.rest_update(
                    "factory_schedules",
                    {
                        "last_status": "skipped_outside_window",
                        "last_error": None,
                        "next_run_at": next_run_at,
                        "updated_at": _utc_now().isoformat(),
                    },
                    {"id": f"eq.{schedule['id']}"},
                )
                processed.append({"schedule": schedule.get("schedule_name"), "skill": skill_name, "status": "skipped_outside_window", "next_run_at": next_run_at})
                continue
            started_at = _utc_now()
            run_folio = self._next_run_folio(db)
            run_row = {
                "folio": run_folio,
                "schedule_id": schedule.get("id"),
                "schedule_folio": schedule.get("folio"),
                "schedule_name": schedule.get("schedule_name"),
                "empresa_id": schedule.get("empresa_id"),
                "project_code": schedule.get("project_code"),
                "module_code": schedule.get("module_code"),
                "skill_name": skill_name,
                "status": "running",
                "started_at": started_at.isoformat(),
            }
            db.rest_insert("factory_schedule_runs", run_row)
            try:
                result_run = runner.run(skill_name, skill_context, source=self._source(source))
            except Exception as exc:
                result_run = {"ok": False, "error": str(exc)}

            finished_at = _utc_now()
            status = "ok" if result_run.get("ok") else "error"
            next_run_at = _next_after(schedule, finished_at)
            next_status = "disabled" if (schedule.get("schedule_type") == "once") else "active"
            error = None if result_run.get("ok") else str(result_run.get("error") or "error")
            db.rest_update(
                "factory_schedule_runs",
                {"status": status, "finished_at": finished_at.isoformat(), "result": result_run, "error": error},
                {"folio": f"eq.{run_folio}"},
            )
            db.rest_update(
                "factory_schedules",
                {
                    "last_run_at": finished_at.isoformat(),
                    "last_status": status,
                    "last_error": error,
                    "last_result": result_run,
                    "next_run_at": next_run_at,
                    "status": next_status,
                    "updated_at": finished_at.isoformat(),
                },
                {"id": f"eq.{schedule['id']}"},
            )
            processed.append({"schedule": schedule.get("schedule_name"), "skill": skill_name, "status": status, "next_run_at": next_run_at})
        return {"ok": True, "data": {"processed": processed, "count": len(processed)}}

    def _runner(self) -> SkillRunner:
        base = Path(__file__).resolve().parents[5]
        skills_dir = base / "factory" / "skills"
        ext = skills_dir / "externos"
        ext.mkdir(parents=True, exist_ok=True)
        self._meta_root = str(skills_dir / "meta")
        self._eval_root = str(skills_dir / "eval")
        return SkillRunner(SkillLoader(internal_root=skills_dir / "internos", external_root=ext))

    def _source(self, source: str):
        if source == "meta":
            return self._meta_root
        if source == "eval":
            return self._eval_root
        return source

    def _next_run_folio(self, db: SupabaseClient) -> str:
        result = db.rest_select("factory_schedule_runs", select="folio", order="folio.desc", limit=1)
        rows = result.get("data") or [] if result.get("ok") else []
        if not rows:
            return "FSRUN-00001"
        try:
            num = int(str(rows[0].get("folio", "FSRUN-00000")).split("-")[-1]) + 1
        except Exception:
            num = 1
        return f"FSRUN-{num:05d}"
