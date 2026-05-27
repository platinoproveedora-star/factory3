"""Handler de /timelog y /pomodoro para el bot admin de factory3."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


_CLIENTS_ROOT  = "companies/EMP_FREELANCE_GROWTH/clients"
_POMODORO_MINS = 20
_BREAK_MINS    = 5


class TimelogRunService:

    def ejecutar(self, context: dict) -> dict:
        text  = (context.get("text") or context.get("message", {}).get("text") or "").strip()
        state = context.get("state") or {}

        # Verificar pomodoro activo en cada mensaje
        pom_alert = self._check_pomodoro(state)

        if text.startswith("/pomodoro"):
            result = self._handle_pomodoro(text, state)
        elif text.startswith("/tiempo") or text.startswith("/timelog"):
            result = self._handle_timelog(text, state)
        else:
            result = self._lista_proyectos(state)

        # Adjuntar alerta de pomodoro si aplica
        if pom_alert:
            result["response"] = pom_alert + "\n\n" + result.get("response", "")

        return result

    # ── pomodoro ─────────────────────────────────────────────────────────────

    def _handle_pomodoro(self, text: str, state: dict) -> dict:
        parts = text.split()
        cmd   = parts[1].lower() if len(parts) > 1 else "status"

        if cmd == "start":
            new_state = {**state, "pomodoro": {
                "active":    True,
                "started_at": self._now(),
                "phase":     "work",   # work | break
                "cycles":    0,
            }}
            return {
                "response": (
                    f"🍅 <b>Pomodoro iniciado</b>\n"
                    f"Trabaja {_POMODORO_MINS} min. Te aviso cuando sea hora de descansar.\n"
                    f"Usa /pomodoro stop para detenerlo."
                ),
                "state": new_state,
            }

        elif cmd == "stop":
            pom   = state.get("pomodoro") or {}
            ciclos = pom.get("cycles", 0)
            new_state = {**state}
            new_state.pop("pomodoro", None)
            return {
                "response": f"⏹ Pomodoro detenido. Completaste <b>{ciclos}</b> ciclos.",
                "state":    new_state,
            }

        else:  # status
            pom = state.get("pomodoro") or {}
            if not pom.get("active"):
                return {"response": "⏸ No hay pomodoro activo.\nUsa /pomodoro start para iniciar.", "state": state}
            mins = self._mins_since(pom.get("started_at", ""))
            phase = pom.get("phase", "work")
            limit = _POMODORO_MINS if phase == "work" else _BREAK_MINS
            left  = max(0, limit - int(mins))
            return {
                "response": (
                    f"🍅 Pomodoro activo — fase: <b>{'Trabajo' if phase == 'work' else 'Descanso'}</b>\n"
                    f"Tiempo en fase: {int(mins)} min\n"
                    f"Faltan aprox: {left} min\n"
                    f"Ciclos completados: {pom.get('cycles', 0)}"
                ),
                "state": state,
            }

    def _check_pomodoro(self, state: dict) -> str:
        """Retorna mensaje de alerta si es hora de cambiar fase. Actualiza state en lugar."""
        pom = state.get("pomodoro")
        if not pom or not pom.get("active"):
            return ""
        mins  = self._mins_since(pom.get("started_at", ""))
        phase = pom.get("phase", "work")
        limit = _POMODORO_MINS if phase == "work" else _BREAK_MINS

        if mins >= limit:
            if phase == "work":
                pom["phase"]      = "break"
                pom["started_at"] = self._now()
                pom["cycles"]     = pom.get("cycles", 0) + 1
                state["pomodoro"] = pom
                return f"🔔 <b>Tiempo de descanso {_BREAK_MINS} min!</b> Ya completaste {pom['cycles']} ciclo(s). Descansa y vuelve. 🍵"
            else:
                pom["phase"]      = "work"
                pom["started_at"] = self._now()
                state["pomodoro"] = pom
                return f"🍅 <b>A trabajar! {_POMODORO_MINS} min de enfoque.</b>"
        return ""

    # ── timelog ───────────────────────────────────────────────────────────────

    def _handle_timelog(self, text: str, state: dict) -> dict:
        """
        Formatos:
          /timelog                    → lista todos los proyectos
          /timelog UC-101             → status del cliente
          /tiempo UC-101 PROY-001 2.5 notas opcionales
        """
        parts = text.split(maxsplit=4)
        cmd   = parts[0].lower()

        # /tiempo UC-101 PROY-001 2.5 [notas]
        if cmd == "/tiempo" and len(parts) >= 4:
            client_id  = parts[1].upper()
            project_id = parts[2].upper()
            try:
                hours = float(parts[3])
            except ValueError:
                return {"response": "❌ Formato: /tiempo UC-101 PROY-001 2.5 notas opcionales", "state": state}
            notes = parts[4] if len(parts) > 4 else ""
            return self._log_hours(client_id, project_id, hours, notes, state)

        # /timelog UC-101
        if len(parts) >= 2 and parts[1].startswith("UC-"):
            return self._status_cliente(parts[1].upper(), state)

        # /timelog → lista todos
        return self._lista_proyectos(state)

    def _lista_proyectos(self, state: dict) -> dict:
        root = Path(_CLIENTS_ROOT)
        if not root.exists():
            return {"response": "📂 No hay clientes registrados todavía.", "state": state}

        lines = ["📋 <b>Proyectos activos</b>\n"]
        found = 0
        for client_dir in sorted(root.iterdir()):
            if not client_dir.is_dir() or client_dir.name == "registry.json":
                continue
            client_id  = client_dir.name
            proj_root  = client_dir / "projects"
            if not proj_root.exists():
                continue
            for proj_dir in sorted(proj_root.iterdir()):
                if not proj_dir.is_dir():
                    continue
                tl = self._read_log(proj_dir / "time_log.json")
                pj = self._read_json(proj_dir / "project.json")
                name      = pj.get("project_name", proj_dir.name) if pj else proj_dir.name
                total_hrs = tl.get("total_hours", 0) if tl else 0
                deadline  = tl.get("deadline", pj.get("deadline", "")) if tl else (pj.get("deadline", "") if pj else "")
                days_left = self._days_left(deadline)
                dl_str    = f"📅 {days_left}d" if days_left is not None else "sin deadline"
                lines.append(f"• <b>{client_id}/{proj_dir.name}</b> — {name}\n  ⏱ {total_hrs:.1f}h | {dl_str}")
                found += 1

        if not found:
            return {"response": "📂 No hay proyectos con time_log todavía.", "state": state}

        lines.append("\n<i>/timelog UC-101 para detalle | /tiempo UC-101 PROY-001 2.5 para registrar horas</i>")
        return {"response": "\n".join(lines), "state": state}

    def _status_cliente(self, client_id: str, state: dict) -> dict:
        root     = Path(_CLIENTS_ROOT) / client_id / "projects"
        if not root.exists():
            return {"response": f"❌ {client_id} no tiene proyectos registrados.", "state": state}

        lines = [f"📁 <b>{client_id}</b>\n"]
        for proj_dir in sorted(root.iterdir()):
            if not proj_dir.is_dir():
                continue
            tl        = self._read_log(proj_dir / "time_log.json")
            pj        = self._read_json(proj_dir / "project.json")
            name      = pj.get("project_name", proj_dir.name) if pj else proj_dir.name
            total_hrs = tl.get("total_hours", 0) if tl else 0
            deadline  = tl.get("deadline", pj.get("deadline", "")) if tl else (pj.get("deadline", "") if pj else "")
            days_left = self._days_left(deadline)
            alert_ev  = tl.get("alerts", {}).get("every_hours", 10) if tl else 10
            next_al   = alert_ev - (total_hrs % alert_ev) if total_hrs % alert_ev else alert_ev
            dl_str    = f"{days_left} días restantes" if days_left is not None else "sin deadline"
            lines.append(
                f"<b>{proj_dir.name}</b> — {name}\n"
                f"  ⏱ {total_hrs:.1f} hrs trabajadas\n"
                f"  📅 {dl_str}\n"
                f"  🔔 Próxima alerta en {next_al:.1f} hrs"
            )

        return {"response": "\n".join(lines), "state": state}

    def _log_hours(self, client_id: str, project_id: str, hours: float, notes: str, state: dict) -> dict:
        log_path = Path(_CLIENTS_ROOT) / client_id / "projects" / project_id / "time_log.json"
        tl = self._read_log(log_path)
        if not tl:
            return {"response": f"❌ No existe time_log para {client_id}/{project_id}.\nInicia el proyecto primero.", "state": state}

        tl["hour_blocks"] = tl.get("hour_blocks", [])
        tl["hour_blocks"].append({"logged_at": self._now(), "hours": hours, "notes": notes})
        tl["total_hours"] = round(tl.get("total_hours", 0) + hours, 2)

        # Verificar alerta
        alert_ev   = tl.get("alerts", {}).get("every_hours", 10)
        last_alert = tl.get("last_alert_at_hours", 0)
        total      = tl["total_hours"]
        days_left  = self._days_left(tl.get("deadline", ""))
        alert_msg  = ""

        if total - last_alert >= alert_ev:
            tl["last_alert_at_hours"] = total
            dl_str    = f"📅 {days_left} días restantes" if days_left is not None else "⚠️ Sin deadline"
            alert_msg = f"\n\n🔔 <b>Alerta: {total:.0f} horas trabajadas en {client_id}/{project_id}</b>\n{dl_str}"

        log_path.write_text(json.dumps(tl, indent=2, ensure_ascii=False), encoding="utf-8")
        dl_str = f"{days_left} días restantes" if days_left is not None else "sin deadline"

        return {
            "response": (
                f"✅ <b>+{hours} hrs</b> registradas en {client_id}/{project_id}\n"
                f"Total: {total:.1f} hrs | {dl_str}"
                + (f"\n📝 {notes}" if notes else "")
                + alert_msg
            ),
            "state": state,
        }

    # ── utils ─────────────────────────────────────────────────────────────────

    def _read_log(self, path: Path) -> dict:
        return self._read_json(path)

    def _read_json(self, path: Path) -> dict:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def _mins_since(self, iso: str) -> float:
        if not iso:
            return 0
        try:
            dt   = datetime.fromisoformat(iso.replace("Z", "+00:00"))
            diff = (datetime.now(timezone.utc) - dt).total_seconds() / 60
            return max(0, diff)
        except Exception:
            return 0

    def _days_left(self, deadline: str) -> int | None:
        if not deadline:
            return None
        try:
            dl   = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
            diff = (dl - datetime.now(timezone.utc)).days
            return max(diff, 0)
        except Exception:
            return None
