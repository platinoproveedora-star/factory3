from __future__ import annotations

from pathlib import Path

from factory.engine import SupabaseClient

_SCHEMA = "fleet4all"


def _runner():
    from factory.engine import SkillLoader, SkillRunner

    root = Path(__file__).resolve().parents[2]
    return SkillRunner(SkillLoader(internal_root=root))


class DeviationAlertService:
    def ejecutar(self, context: dict) -> dict:
        empresa_id = str(context.get("empresa_id") or "").strip()
        if not empresa_id:
            return {"ok": False, "error": "empresa_id_requerido"}

        lang = str(context.get("language") or "es").strip().lower()
        if lang not in ("es", "en"):
            lang = "es"

        db = SupabaseClient({**context, "schema": _SCHEMA})
        res = db.rest_select(
            "fuel_efficiency",
            filters={"empresa_id": f"eq.{empresa_id}"},
            select="unit_key,period_from,period_to,km_per_liter,expected_km_per_liter,deviation_pct,flag",
        )
        if not res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": res.get("error")}}
        rows = res.get("data") or []

        last_by_unit: dict[str, dict] = {}
        for row in rows:
            unit_key = row.get("unit_key")
            current = last_by_unit.get(unit_key)
            if not current or (row.get("period_to") or "") > (current.get("period_to") or ""):
                last_by_unit[unit_key] = row

        flagged = [row for row in last_by_unit.values() if row.get("flag") in ("warning", "alert")]

        dry_run = context.get("dry_run", True)
        send_channel = context.get("send_channel")
        alerts = []
        warnings: list[str] = []
        for row in flagged:
            message = self._draft_message(row, lang)
            item = {"unit_key": row.get("unit_key"), "flag": row.get("flag"), "message": message, "sent": False}
            if not dry_run and send_channel:
                send_res = _runner().run(send_channel, {"to": row.get("unit_key"), "message": message})
                item["sent"] = bool(send_res.get("ok"))
                if not send_res.get("ok"):
                    warnings.append(f"send_failed:{row.get('unit_key')}:{send_res.get('error')}")
            alerts.append(item)

        return {"ok": True, "data": {"alerts": alerts, "warnings": warnings}}

    def _draft_message(self, row: dict, lang: str) -> str:
        instruction = (
            "Redacta una alerta breve y profesional de rendimiento de combustible para una unidad de flotilla."
            if lang == "es"
            else "Write a brief, professional fuel efficiency alert for a fleet unit."
        )
        prompt = (
            f"{instruction}\n\n"
            f"Unidad: {row.get('unit_key')}\n"
            f"km/litro actual: {row.get('km_per_liter')}\n"
            f"km/litro esperado: {row.get('expected_km_per_liter')}\n"
            f"Desviacion: {row.get('deviation_pct')}%\n"
            f"Nivel: {row.get('flag')}\n\n"
            "Usa solo estos datos. No inventes causas."
        )
        result = _runner().run("vertical_factory_utils/ai_interpreter", {"mode": "chat", "text": prompt})
        if not result.get("ok"):
            return self._fallback_message(row, lang)
        return (result.get("data") or {}).get("response") or self._fallback_message(row, lang)

    def _fallback_message(self, row: dict, lang: str) -> str:
        if lang == "en":
            return f"Unit {row.get('unit_key')}: fuel efficiency deviation {row.get('deviation_pct')}% ({row.get('flag')})."
        return f"Unidad {row.get('unit_key')}: desviacion de rendimiento {row.get('deviation_pct')}% ({row.get('flag')})."
