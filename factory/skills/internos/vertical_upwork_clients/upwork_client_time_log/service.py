"""Time log por proyecto — registra horas y avisa por Telegram cada N horas."""
from __future__ import annotations

import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


_BOT_TOKEN_ENV  = "FACTORY3_ADMIN_BOT_TOKEN"
_CHAT_ID_ENV    = "TELEGRAM_OWNER_CHAT_ID"
_TELEGRAM_URL   = "https://api.telegram.org/bot{token}/sendMessage"


class UpworkClientTimeLogService:

    def ejecutar(self, context: dict) -> dict:
        client_id  = (context.get("client_id") or "").strip()
        project_id = (context.get("project_id") or "PROY-001").strip()
        action     = (context.get("action") or "status").lower()
        dry_run    = context.get("dry_run", False)

        if not client_id:
            return {"ok": False, "error": "client_id requerido (ej. UC-101)"}

        root     = Path(context.get("clients_root") or "companies/EMP_FREELANCE_GROWTH/clients")
        log_path = root / client_id / "projects" / project_id / "time_log.json"

        if action == "start":
            return self._start(log_path, context, dry_run)
        elif action == "log":
            return self._log_hours(log_path, context, dry_run)
        elif action == "status":
            return self._status(log_path, client_id, project_id)
        elif action == "check":
            return self._check_alerts(log_path, client_id, project_id, dry_run)
        else:
            return {"ok": False, "error": f"action invalido: {action}. Usa: start | log | status | check"}

    # ── actions ───────────────────────────────────────────────────────────────

    def _start(self, log_path: Path, context: dict, dry_run: bool) -> dict:
        deadline = context.get("deadline", "")
        alert_hours = int(context.get("alert_every_hours", 10))
        data = {
            "started_at":           self._now(),
            "deadline":             deadline,
            "total_hours":          0.0,
            "last_alert_at_hours":  0.0,
            "hour_blocks":          [],
            "alerts": {
                "every_hours": alert_hours,
                "enabled":     True,
            },
        }
        if not dry_run:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return {"ok": True, "data": {"action": "start", "log": data, "path": str(log_path)}}

    def _log_hours(self, log_path: Path, context: dict, dry_run: bool) -> dict:
        hours = float(context.get("hours", 0))
        notes = context.get("notes", "")
        if hours <= 0:
            return {"ok": False, "error": "hours debe ser mayor a 0"}

        data = self._read(log_path)
        if not data:
            return {"ok": False, "error": f"time_log.json no encontrado. Corre action=start primero: {log_path}"}

        block = {"start": self._now(), "hours": hours, "notes": notes}
        data["hour_blocks"].append(block)
        data["total_hours"] = round(data.get("total_hours", 0) + hours, 2)

        # Verificar alerta cada N horas
        alert_every = data.get("alerts", {}).get("every_hours", 10)
        last_alert  = data.get("last_alert_at_hours", 0)
        total       = data["total_hours"]
        alert_sent  = False

        if total - last_alert >= alert_every:
            days_left = self._days_left(data.get("deadline", ""))
            msg = (
                f"⏱ <b>{log_path.parent.parent.parent.name}/{log_path.parent.name}</b>\n"
                f"Horas trabajadas: <b>{total:.1f} hrs</b>\n"
                f"Bloque actual: {hours} hrs — {notes or 'sin nota'}\n"
                f"{'📅 Días restantes: <b>' + str(days_left) + ' días</b>' if days_left is not None else '⚠️ Sin deadline definido'}"
            )
            if not dry_run:
                self._telegram(msg)
                data["last_alert_at_hours"] = total
            alert_sent = True

        if not dry_run:
            log_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

        return {"ok": True, "data": {
            "action":      "log",
            "hours_added": hours,
            "total_hours": data["total_hours"],
            "alert_sent":  alert_sent,
            "days_left":   self._days_left(data.get("deadline", "")),
        }}

    def _status(self, log_path: Path, client_id: str, project_id: str) -> dict:
        data = self._read(log_path)
        if not data:
            return {"ok": True, "data": {"status": "no_iniciado", "client_id": client_id, "project_id": project_id}}

        total     = data.get("total_hours", 0)
        days_left = self._days_left(data.get("deadline", ""))
        alert_every = data.get("alerts", {}).get("every_hours", 10)
        next_alert  = alert_every - (total % alert_every) if total % alert_every else alert_every

        return {"ok": True, "data": {
            "client_id":        client_id,
            "project_id":       project_id,
            "started_at":       data.get("started_at"),
            "deadline":         data.get("deadline"),
            "total_hours":      total,
            "days_left":        days_left,
            "next_alert_in":    round(next_alert, 1),
            "blocks":           len(data.get("hour_blocks", [])),
        }}

    def _check_alerts(self, log_path: Path, client_id: str, project_id: str, dry_run: bool) -> dict:
        data = self._read(log_path)
        if not data:
            return {"ok": False, "error": "time_log.json no encontrado"}

        total       = data.get("total_hours", 0)
        last_alert  = data.get("last_alert_at_hours", 0)
        alert_every = data.get("alerts", {}).get("every_hours", 10)
        days_left   = self._days_left(data.get("deadline", ""))

        if total - last_alert >= alert_every:
            msg = (
                f"⏱ <b>{client_id}/{project_id}</b>\n"
                f"Horas trabajadas: <b>{total:.1f} hrs</b>\n"
                f"{'📅 Días restantes: <b>' + str(days_left) + ' días</b>' if days_left is not None else '⚠️ Sin deadline'}"
            )
            if not dry_run:
                self._telegram(msg)
                data["last_alert_at_hours"] = total
                log_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            return {"ok": True, "data": {"alert_sent": True, "total_hours": total, "days_left": days_left}}

        return {"ok": True, "data": {"alert_sent": False, "total_hours": total, "next_alert_in": round(alert_every - (total - last_alert), 1)}}

    # ── helpers ───────────────────────────────────────────────────────────────

    def _read(self, path: Path) -> dict:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def _days_left(self, deadline: str) -> int | None:
        if not deadline:
            return None
        try:
            dl = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
            diff = (dl - datetime.now(timezone.utc)).days
            return max(diff, 0)
        except Exception:
            return None

    def _telegram(self, text: str) -> None:
        token   = os.getenv(_BOT_TOKEN_ENV, "")
        chat_id = os.getenv(_CHAT_ID_ENV, "")
        if not token or not chat_id:
            return
        payload = json.dumps({"chat_id": chat_id, "text": text, "parse_mode": "HTML"}).encode()
        req = urllib.request.Request(
            _TELEGRAM_URL.format(token=token),
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(req, timeout=10)
        except Exception:
            pass
