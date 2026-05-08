"""Service for rh_offer_sender — genera y envía carta oferta por Telegram."""
from __future__ import annotations
import importlib.util, os, sys
from pathlib import Path

_BASE = Path(__file__).parent.parent.parent.parent.parent

_OFERTA_TEMPLATE = """\
Hola {nombre}, nos da gusto informarte que has sido seleccionado(a).

Puesto: {puesto}
Salario: {salario}
Horario: {horario}
Fecha de inicio: {fecha_inicio}
Lugar: {lugar}

{notas}

Para ACEPTAR responde: SI
Para declinar responde: NO

Esta oferta es válida por 24 horas.
"""


class RhOfferSenderService:

    def ejecutar(self, context: dict) -> dict:
        candidato_id  = context.get("candidato_id")
        vacante_id    = context.get("vacante_id", "")
        canal_user_id = context.get("canal_user_id")
        oferta        = context.get("oferta", {})
        dry_run       = context.get("dry_run", False)

        if not canal_user_id and candidato_id:
            canal_user_id = self._obtener_canal_user_id(candidato_id)

        if not canal_user_id:
            return {"ok": False, "error": "canal_user_id requerido (o candidato_id con canal_user_id en DB)"}

        mensaje = self._armar_mensaje(oferta, candidato_id)

        if dry_run:
            return {"ok": True, "data": {"enviado": False, "dry_run": True, "mensaje": mensaje}}

        resultado = self._enviar(canal_user_id, mensaje)
        if not resultado["ok"]:
            return resultado

        if candidato_id:
            self._registrar(candidato_id, vacante_id, mensaje)

        return {
            "ok": True,
            "data": {
                "enviado":      True,
                "canal_user_id": canal_user_id,
                "mensaje":      mensaje,
            },
        }

    def _armar_mensaje(self, oferta: dict, candidato_id: str | None) -> str:
        nombre      = oferta.get("nombre", "Candidato")
        puesto      = oferta.get("puesto", "Puesto por confirmar")
        salario     = oferta.get("salario", "A convenir")
        horario     = oferta.get("horario", "Por confirmar")
        fecha_inicio = oferta.get("fecha_inicio", "Por confirmar")
        lugar       = oferta.get("lugar", "Por confirmar")
        notas       = oferta.get("notas", "")

        if not nombre or nombre == "Candidato":
            nombre = self._obtener_nombre(candidato_id) or "Candidato"

        return _OFERTA_TEMPLATE.format(
            nombre=nombre, puesto=puesto, salario=salario,
            horario=horario, fecha_inicio=fecha_inicio,
            lugar=lugar, notas=notas,
        ).strip()

    def _enviar(self, chat_id: str, mensaje: str) -> dict:
        skill_path = _BASE / "factory" / "skills" / "internos" / "telegram_send_message" / "skill.py"
        if not skill_path.exists():
            return {"ok": False, "error": "telegram_send_message no encontrado"}
        sys.modules.pop("service", None)
        skill_dir = str(skill_path.parent)
        inserted  = skill_dir not in sys.path
        if inserted:
            sys.path.insert(0, skill_dir)
        try:
            spec = importlib.util.spec_from_file_location("skill_tg_offer", skill_path)
            mod  = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.run({"chat_id": chat_id, "text": mensaje})
        except Exception as e:
            return {"ok": False, "error": str(e)}
        finally:
            if inserted and sys.path and sys.path[0] == skill_dir:
                sys.path.pop(0)
            sys.modules.pop("service", None)

    def _obtener_canal_user_id(self, candidato_id: str) -> str | None:
        try:
            from factory.engine import SupabaseClient
            sb   = SupabaseClient({})
            resp = sb.rest_select("candidatos", {"id": candidato_id}, select="canal_user_id", limit=1)
            return ((resp.get("data") or [{}])[0]).get("canal_user_id")
        except Exception:
            return None

    def _obtener_nombre(self, candidato_id: str | None) -> str | None:
        if not candidato_id:
            return None
        try:
            from factory.engine import SupabaseClient
            sb   = SupabaseClient({})
            resp = sb.rest_select("candidatos", {"id": candidato_id}, select="nombre", limit=1)
            return ((resp.get("data") or [{}])[0]).get("nombre")
        except Exception:
            return None

    def _registrar(self, candidato_id: str, vacante_id: str, mensaje: str) -> None:
        try:
            from factory.engine import SupabaseClient
            sb = SupabaseClient({})
            sb.rest_insert("alertas", {
                "candidato_id": candidato_id,
                "tipo":         "oferta_enviada",
                "canal":        "telegram",
                "mensaje":      mensaje[:500],
                "enviado":      True,
            }).execute()
        except Exception:
            pass
