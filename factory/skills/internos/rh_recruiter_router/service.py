"""Service for rh_recruiter_router — asigna candidato al reclutador y notifica por Telegram."""

from __future__ import annotations
import importlib.util
import os
import sys
from pathlib import Path


class RhRecruiterRouterService:

    def ejecutar(self, context: dict) -> dict:
        valido, error = self._validar(context)
        if not valido:
            return {"ok": False, "error": error}

        candidato_id = context["candidato_id"]
        empresa_id = context.get("empresa_id", "")
        zona = context.get("zona", "")
        base_dir = Path(context.get("base_dir", "factory"))
        dry_run = context.get("dry_run", False)

        reclutador = self._buscar_reclutador(empresa_id, zona)
        if not reclutador["ok"]:
            return reclutador

        rec = reclutador["data"]
        candidato = self._obtener_candidato(candidato_id)

        mensaje = self._armar_mensaje(candidato, rec)

        notif = {"ok": True, "dry_run": True}
        if not dry_run and rec.get("telegram_chat_id"):
            notif = self._notificar(rec["telegram_chat_id"], mensaje, base_dir)

        return {
            "ok": True,
            "data": {
                "candidato_id": candidato_id,
                "reclutador_id": rec.get("id"),
                "reclutador_nombre": rec.get("nombre"),
                "telegram_chat_id": rec.get("telegram_chat_id"),
                "mensaje_enviado": mensaje,
                "notificacion": notif,
            },
        }

    def _buscar_reclutador(self, empresa_id: str, zona: str) -> dict:
        try:
            from factory.engine import SupabaseClient
            sb = SupabaseClient({})

            filters: dict = {"activo": "eq.true"}
            if empresa_id:
                filters["empresa_id"] = empresa_id
            if zona:
                filters["zona"] = zona

            resp = sb.rest_select("reclutadores", filters, limit=1)
            recs = resp.get("data") or []

            if not recs:
                resp2 = sb.rest_select("reclutadores", {"activo": "eq.true"}, limit=1)
                recs  = resp2.get("data") or []

            if not recs:
                return {"ok": False, "error": "no hay reclutadores activos disponibles"}

            return {"ok": True, "data": recs[0]}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _obtener_candidato(self, candidato_id: str) -> dict:
        try:
            from factory.engine import SupabaseClient
            sb   = SupabaseClient({})
            resp = sb.rest_select("candidatos", {"id": candidato_id}, select="id,nombre,telefono,folio,estado,vacante_id", limit=1)
            return (resp.get("data") or [{}])[0]
        except Exception:
            return {"id": candidato_id}

    def _armar_mensaje(self, candidato: dict, reclutador: dict) -> str:
        nombre = candidato.get("nombre", "Candidato sin nombre")
        folio = candidato.get("folio", candidato.get("id", ""))[:8]
        telefono = candidato.get("telefono", "no disponible")
        estado = candidato.get("estado", "apto")
        return (
            f"Nuevo candidato calificado asignado a ti:\n\n"
            f"Nombre: {nombre}\n"
            f"Folio: {folio}\n"
            f"Tel: {telefono}\n"
            f"Estado: {estado}\n\n"
            f"Contáctalo a la brevedad."
        )

    def _notificar(self, chat_id: str, mensaje: str, base_dir: Path) -> dict:
        skill_path = base_dir / "skills" / "internos" / "telegram_send_message" / "skill.py"
        if not skill_path.exists():
            return {"ok": False, "error": "telegram_send_message no encontrado"}
        sys.modules.pop("service", None)
        skill_dir = str(skill_path.parent)
        inserted = skill_dir not in sys.path
        if inserted:
            sys.path.insert(0, skill_dir)
        try:
            spec = importlib.util.spec_from_file_location("skill_tg", skill_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.run({"chat_id": chat_id, "text": mensaje})
        except Exception as e:
            return {"ok": False, "error": str(e)}
        finally:
            if inserted and sys.path and sys.path[0] == skill_dir:
                sys.path.pop(0)
            sys.modules.pop("service", None)

    def _validar(self, context: dict) -> tuple[bool, str | None]:
        if not context.get("candidato_id"):
            return False, "candidato_id es requerido"
        return True, None
