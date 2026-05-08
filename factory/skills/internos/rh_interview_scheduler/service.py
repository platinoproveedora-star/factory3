"""Service for rh_interview_scheduler — agenda entrevistas y notifica por Telegram."""

from __future__ import annotations
import importlib.util
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path


_DURACION_MIN_DEFAULT = 30
_BASE = Path(__file__).parent.parent.parent.parent.parent


class RhInterviewSchedulerService:

    def ejecutar(self, context: dict) -> dict:
        accion = context.get("accion", "agendar")

        if accion == "agendar":
            return self._agendar(context)
        if accion == "cancelar":
            return self._cancelar(context)
        if accion == "listar":
            return self._listar(context)
        return {"ok": False, "error": f"accion inválida: '{accion}'. Usa: agendar, cancelar, listar"}

    # ── Agendar ───────────────────────────────────────────────────────────────

    def _agendar(self, context: dict) -> dict:
        candidato_id    = context.get("candidato_id")
        reclutador_id   = context.get("reclutador_id")
        vacante_id      = context.get("vacante_id", "")
        fecha_hora      = context.get("fecha_hora")
        duracion_min    = int(context.get("duracion_min", _DURACION_MIN_DEFAULT))
        tipo            = context.get("tipo", "presencial")
        notas           = context.get("notas", "")
        dry_run         = context.get("dry_run", False)
        notify_candidato = context.get("notify_candidato", True)
        notify_reclutador = context.get("notify_reclutador", True)

        if not candidato_id:
            return {"ok": False, "error": "candidato_id es requerido"}
        if not fecha_hora:
            fecha_hora = self._siguiente_slot(reclutador_id)

        entrevista = {
            "candidato_id":  candidato_id,
            "reclutador_id": reclutador_id or "",
            "vacante_id":    vacante_id,
            "fecha_hora":    fecha_hora,
            "duracion_min":  duracion_min,
            "tipo":          tipo,
            "estado":        "agendada",
            "notas":         notas,
        }

        entrevista_id = None
        if not dry_run:
            result = self._guardar_entrevista(entrevista)
            if not result["ok"]:
                return result
            entrevista_id = result["data"].get("id")

        notificaciones = {}
        if not dry_run:
            cand_info  = self._obtener_candidato(candidato_id)
            rec_info   = self._obtener_reclutador(reclutador_id) if reclutador_id else {}

            if notify_candidato and cand_info.get("canal_user_id"):
                notificaciones["candidato"] = self._notificar(
                    cand_info["canal_user_id"],
                    self._mensaje_candidato(cand_info, fecha_hora, tipo, duracion_min),
                )
            if notify_reclutador and rec_info.get("telegram_chat_id"):
                notificaciones["reclutador"] = self._notificar(
                    rec_info["telegram_chat_id"],
                    self._mensaje_reclutador(cand_info, rec_info, fecha_hora, tipo, vacante_id),
                )

        return {
            "ok": True,
            "data": {
                "entrevista_id": entrevista_id,
                "fecha_hora":    fecha_hora,
                "tipo":          tipo,
                "duracion_min":  duracion_min,
                "dry_run":       dry_run,
                "notificaciones": notificaciones,
            },
        }

    # ── Cancelar ──────────────────────────────────────────────────────────────

    def _cancelar(self, context: dict) -> dict:
        entrevista_id = context.get("entrevista_id")
        if not entrevista_id:
            return {"ok": False, "error": "entrevista_id es requerido para cancelar"}
        try:
            from factory.engine import SupabaseClient
            sb = SupabaseClient({})
            sb.rest_update("entrevistas", {"estado": "cancelada"}, {"id": entrevista_id})
            return {"ok": True, "data": {"entrevista_id": entrevista_id, "estado": "cancelada"}}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ── Listar ────────────────────────────────────────────────────────────────

    def _listar(self, context: dict) -> dict:
        reclutador_id = context.get("reclutador_id")
        candidato_id  = context.get("candidato_id")
        estado        = context.get("estado", "agendada")
        try:
            from factory.engine import SupabaseClient
            sb      = SupabaseClient({})
            filters = {"estado": estado}
            if reclutador_id:
                filters["reclutador_id"] = reclutador_id
            if candidato_id:
                filters["candidato_id"] = candidato_id
            r = sb.rest_select("entrevistas", filters, order="fecha_hora")
            return {"ok": True, "data": {"entrevistas": r.get("data") or []}}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _siguiente_slot(self, reclutador_id: str | None) -> str:
        base = datetime.now().replace(minute=0, second=0, microsecond=0) + timedelta(hours=24)
        if base.weekday() >= 5:
            base += timedelta(days=(7 - base.weekday()))
        base = base.replace(hour=9)
        return base.strftime("%Y-%m-%d %H:%M")

    def _guardar_entrevista(self, entrevista: dict) -> dict:
        try:
            from factory.engine import SupabaseClient
            sb   = SupabaseClient({})
            resp = sb.rest_insert("entrevistas", entrevista)
            rec  = (resp.get("data") or [{}])
            rec  = rec[0] if isinstance(rec, list) else rec
            return {"ok": True, "data": rec}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _obtener_candidato(self, candidato_id: str) -> dict:
        try:
            from factory.engine import SupabaseClient
            sb   = SupabaseClient({})
            resp = sb.rest_select("candidatos", {"id": candidato_id}, select="nombre,telefono,canal_user_id", limit=1)
            return ((resp.get("data") or [{}])[0])
        except Exception:
            return {}

    def _obtener_reclutador(self, reclutador_id: str) -> dict:
        try:
            from factory.engine import SupabaseClient
            sb   = SupabaseClient({})
            resp = sb.rest_select("reclutadores", {"id": reclutador_id}, select="nombre,telegram_chat_id", limit=1)
            return ((resp.get("data") or [{}])[0])
        except Exception:
            return {}

    def _notificar(self, chat_id: str, mensaje: str) -> dict:
        skill_path = _BASE / "factory" / "skills" / "internos" / "telegram_send_message" / "skill.py"
        if not skill_path.exists():
            return {"ok": False, "error": "telegram_send_message no encontrado"}
        sys.modules.pop("service", None)
        skill_dir = str(skill_path.parent)
        inserted  = skill_dir not in sys.path
        if inserted:
            sys.path.insert(0, skill_dir)
        try:
            spec = importlib.util.spec_from_file_location("skill_tg_sched", skill_path)
            mod  = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.run({"chat_id": chat_id, "text": mensaje})
        except Exception as e:
            return {"ok": False, "error": str(e)}
        finally:
            if inserted and sys.path and sys.path[0] == skill_dir:
                sys.path.pop(0)
            sys.modules.pop("service", None)

    def _mensaje_candidato(self, cand: dict, fecha_hora: str, tipo: str, duracion: int) -> str:
        nombre = cand.get("nombre", "Candidato")
        return (
            f"Hola {nombre}, tu entrevista ha sido agendada.\n\n"
            f"Fecha: {fecha_hora}\n"
            f"Tipo: {tipo}\n"
            f"Duración aprox: {duracion} minutos\n\n"
            f"Te contactaremos para confirmar detalles."
        )

    def _mensaje_reclutador(self, cand: dict, rec: dict, fecha_hora: str, tipo: str, vacante_id: str) -> str:
        nombre_cand = cand.get("nombre", "Candidato sin nombre")
        tel         = cand.get("telefono", "no disponible")
        return (
            f"Nueva entrevista agendada:\n\n"
            f"Candidato: {nombre_cand}\n"
            f"Tel: {tel}\n"
            f"Fecha: {fecha_hora}\n"
            f"Tipo: {tipo}\n"
            f"Vacante ID: {vacante_id or 'no especificada'}"
        )
