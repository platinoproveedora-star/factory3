"""Romper cristal: descifra con motivo obligatorio + audit log. Sin UI en v1. SOLO server-to-server."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

_VERTICAL = Path(__file__).parent.parent  # vertical_auth_security


class SecuritySupportDecryptSessionService:

    def ejecutar(self, context: dict) -> dict:
        managed_rfc_id  = (context.get("managed_rfc_id") or "").strip()
        motivo          = (context.get("motivo") or "").strip()
        support_user_id = (context.get("support_user_id") or "soporte").strip()

        if not managed_rfc_id:
            return {"ok": False, "error": "managed_rfc_id requerido"}
        if not motivo or len(motivo) < 10:
            return {"ok": False, "error": "motivo requerido (mínimo 10 caracteres)"}

        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run — secreto no descifrado", "data": {"motivo": motivo}}

        # Registrar en audit log ANTES de descifrar
        self._audit_log(context, managed_rfc_id, motivo, support_user_id)

        # Delegar descifrado a security_secret_retrieve
        result = self._run("security_secret_retrieve", {
            **context,
            "managed_rfc_id": managed_rfc_id,
            "dry_run":        False,
        })

        if not result.get("ok"):
            return {"ok": False, "error": f"Error descifrando: {result.get('error', '')}"}

        return {
            "ok":      True,
            "message": f"Secreto descifrado por soporte. Motivo: {motivo}",
            "data":    result.get("data", {}),
        }

    def _audit_log(self, context: dict, managed_rfc_id: str, motivo: str, support_user_id: str) -> None:
        url = (context.get("platform_supabase_url") or
               os.getenv("PLATFORM_SUPABASE_URL", "")).rstrip("/")
        key = (context.get("platform_supabase_service_role_key") or
               os.getenv("PLATFORM_SUPABASE_SERVICE_ROLE_KEY", ""))
        if not url or not key:
            return
        try:
            row = {
                "action":         "support_decrypt",
                "managed_rfc_id": managed_rfc_id,
                "actor":          support_user_id,
                "motivo":         motivo,
                "created_at":     datetime.now(timezone.utc).isoformat(),
            }
            req = urllib.request.Request(
                f"{url}/rest/v1/audit_log",
                data=json.dumps(row).encode("utf-8"),
                headers={
                    "apikey":          key,
                    "Authorization":   f"Bearer {key}",
                    "Content-Type":    "application/json",
                    "Content-Profile": "platform",
                    "Prefer":          "return=minimal",
                    "User-Agent":      "FactoryFactory/0.1 (+https://github.com/)",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                resp.read()
        except Exception:
            pass  # audit log falla silenciosamente — no bloquear operación

    def _run(self, skill_name: str, ctx: dict) -> dict:
        skill_path  = _VERTICAL / skill_name
        entrypoint  = skill_path / "skill.py"
        if not entrypoint.exists():
            return {"ok": False, "error": f"skill no encontrado: {skill_name}"}
        spec = importlib.util.spec_from_file_location(f"_auth_{skill_name}", entrypoint)
        if not spec or not spec.loader:
            return {"ok": False, "error": f"error cargando: {skill_name}"}
        module = importlib.util.module_from_spec(spec)
        sys.path.insert(0, str(skill_path))
        for k in [k for k in sys.modules if k in ("service", "skill")]:
            del sys.modules[k]
        try:
            spec.loader.exec_module(module)
            return module.run(ctx)
        except Exception as e:
            return {"ok": False, "error": str(e)}
        finally:
            if sys.path and sys.path[0] == str(skill_path):
                sys.path.pop(0)
