"""Service for rh_channel_publisher — publica vacante en múltiples canales digitales."""

from __future__ import annotations
import importlib.util
import sys
from pathlib import Path


class RhChannelPublisherService:

    def ejecutar(self, context: dict) -> dict:
        valido, error = self._validar(context)
        if not valido:
            return {"ok": False, "error": error}

        texto = context["texto"]
        canales = context.get("canales", ["facebook"])
        vacante_id = context.get("vacante_id", "")
        empresa_id = context.get("empresa_id", "")
        dry_run = context.get("dry_run", True)
        base_dir = Path(context.get("base_dir", "factory"))

        resultados: dict = {}

        if "facebook" in canales:
            resultados["facebook"] = self._publicar_facebook(
                texto, vacante_id, empresa_id, dry_run, base_dir
            )

        if "whatsapp" in canales:
            resultados["whatsapp"] = self._publicar_whatsapp(
                texto, context.get("whatsapp_destinos", []), vacante_id, empresa_id, dry_run, base_dir
            )

        if "telegram" in canales:
            resultados["telegram"] = self._publicar_telegram(
                texto, context.get("telegram_chat_id"), dry_run, base_dir
            )

        exitosos = sum(1 for r in resultados.values() if r.get("ok"))
        return {
            "ok": exitosos > 0,
            "data": {
                "canales_solicitados": canales,
                "exitosos": exitosos,
                "fallidos": len(canales) - exitosos,
                "resultados": resultados,
            },
        }

    def _publicar_facebook(self, texto, vacante_id, empresa_id, dry_run, base_dir) -> dict:
        skill = self._cargar_skill("facebook_post_publisher", base_dir)
        if not skill:
            return {"ok": False, "error": "facebook_post_publisher no encontrado"}
        return skill.run({
            "texto": texto,
            "vacante_id": vacante_id,
            "empresa_id": empresa_id,
            "dry_run": dry_run,
        })

    def _publicar_whatsapp(self, texto, destinos, vacante_id, empresa_id, dry_run, base_dir) -> dict:
        if not destinos:
            return {"ok": False, "error": "whatsapp_destinos requerido para canal whatsapp"}
        skill = self._cargar_skill("whatsapp_group_broadcaster", base_dir)
        if not skill:
            return {"ok": False, "error": "whatsapp_group_broadcaster no encontrado"}
        resultados = []
        for destino in destinos:
            r = skill.run({
                "destino": destino,
                "texto": texto,
                "vacante_id": vacante_id,
                "empresa_id": empresa_id,
                "dry_run": dry_run,
            })
            resultados.append(r)
        ok = any(r.get("ok") for r in resultados)
        return {"ok": ok, "enviados": len([r for r in resultados if r.get("ok")]), "total": len(destinos)}

    def _publicar_telegram(self, texto, chat_id, dry_run, base_dir) -> dict:
        if not chat_id:
            return {"ok": False, "error": "telegram_chat_id requerido para canal telegram"}
        if dry_run:
            return {"ok": True, "dry_run": True, "chat_id": chat_id}
        skill = self._cargar_skill("telegram_send_message", base_dir)
        if not skill:
            return {"ok": False, "error": "telegram_send_message no encontrado"}
        return skill.run({"chat_id": chat_id, "text": texto})

    def _cargar_skill(self, nombre: str, base_dir: Path):
        skill_path = base_dir / "skills" / "internos" / nombre / "skill.py"
        if not skill_path.exists():
            return None
        sys.modules.pop("service", None)
        skill_dir = str(skill_path.parent)
        inserted = skill_dir not in sys.path
        if inserted:
            sys.path.insert(0, skill_dir)
        try:
            spec = importlib.util.spec_from_file_location(f"skill_{nombre}", skill_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
        except Exception:
            return None
        finally:
            if inserted and sys.path and sys.path[0] == skill_dir:
                sys.path.pop(0)
            sys.modules.pop("service", None)

    def _validar(self, context: dict) -> tuple[bool, str | None]:
        if not context.get("texto"):
            return False, "texto es requerido"
        canales = context.get("canales", [])
        validos = {"facebook", "whatsapp", "telegram"}
        invalidos = set(canales) - validos
        if invalidos:
            return False, f"canales no soportados: {invalidos}. Válidos: {validos}"
        return True, None
