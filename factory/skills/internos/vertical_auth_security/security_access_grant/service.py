"""CRUD de grants de acceso por módulo. Alta manual v1 (sin Stripe)."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request


class SecurityAccessGrantService:

    def ejecutar(self, context: dict) -> dict:
        action      = (context.get("action") or "check").strip()
        user_id     = (context.get("user_id") or "").strip()
        modulo_code = (context.get("modulo_code") or "").strip()

        url = (context.get("platform_supabase_url") or
               os.getenv("PLATFORM_SUPABASE_URL", "")).rstrip("/")
        key = (context.get("platform_supabase_service_role_key") or
               os.getenv("PLATFORM_SUPABASE_SERVICE_ROLE_KEY", ""))

        if not user_id:
            return {"ok": False, "error": "user_id requerido"}
        if not modulo_code:
            return {"ok": False, "error": "modulo_code requerido"}
        if not url or not key:
            return {"ok": False, "error": "Faltan PLATFORM_SUPABASE_URL o PLATFORM_SUPABASE_SERVICE_ROLE_KEY"}

        if action == "create":
            return self._create(context, url, key, user_id, modulo_code)
        if action == "check":
            return self._check(url, key, user_id, modulo_code)
        if action == "delete":
            return self._delete(context, url, key, user_id, modulo_code)
        return {"ok": False, "error": f"action inválido: {action}. Usa create|check|delete"}

    def _create(self, context: dict, url: str, key: str, user_id: str, modulo_code: str) -> dict:
        role = (context.get("role") or "owner").strip()
        if role not in ("owner", "platform_admin"):
            return {"ok": False, "error": "role debe ser owner o platform_admin"}

        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run — grant no creado", "data": {
                "user_id": user_id, "modulo_code": modulo_code, "role": role,
            }}

        try:
            rows = self._pg_post(url, key, {
                "user_id":     user_id,
                "modulo_code": modulo_code,
                "role":        role,
            })
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            if e.code == 409 or "duplicate" in body.lower():
                return {"ok": True, "message": "Grant ya existe", "data": {"created": False}}
            return {"ok": False, "error": f"Supabase {e.code}: {body[:200]}"}

        grant_id = rows[0].get("id") if rows else None
        return {
            "ok":      True,
            "message": f"Acceso otorgado a '{modulo_code}' para user {user_id}",
            "data":    {"grant_id": grant_id, "user_id": user_id, "modulo_code": modulo_code, "role": role},
        }

    def _check(self, url: str, key: str, user_id: str, modulo_code: str) -> dict:
        qs   = (f"?user_id=eq.{urllib.parse.quote(user_id)}"
                f"&modulo_code=eq.{urllib.parse.quote(modulo_code)}"
                f"&select=id,role&limit=1")
        rows = self._pg_get(url, key, f"/rest/v1/access_grants{qs}")
        has  = bool(rows)
        return {
            "ok":      True,
            "message": f"Acceso {'concedido' if has else 'denegado'} a '{modulo_code}'",
            "data":    {"has_access": has, "role": rows[0].get("role") if has else None},
        }

    def _delete(self, context: dict, url: str, key: str, user_id: str, modulo_code: str) -> dict:
        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run — grant no eliminado"}
        qs = (f"?user_id=eq.{urllib.parse.quote(user_id)}"
              f"&modulo_code=eq.{urllib.parse.quote(modulo_code)}")
        self._pg_delete(url, key, f"/rest/v1/access_grants{qs}")
        return {"ok": True, "message": f"Acceso revocado a '{modulo_code}' para user {user_id}"}

    def _pg_get(self, url: str, key: str, path: str) -> list:
        req = urllib.request.Request(f"{url}{path}", headers={
            "apikey": key, "Authorization": f"Bearer {key}",
            "Accept-Profile": "platform",
            "User-Agent": "FactoryFactory/0.1 (+https://github.com/)",
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _pg_post(self, url: str, key: str, row: dict) -> list:
        req = urllib.request.Request(
            f"{url}/rest/v1/access_grants",
            data=json.dumps(row).encode("utf-8"),
            headers={
                "apikey": key, "Authorization": f"Bearer {key}",
                "Content-Type": "application/json", "Content-Profile": "platform",
                "Prefer": "return=representation",
                "User-Agent": "FactoryFactory/0.1 (+https://github.com/)",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _pg_delete(self, url: str, key: str, path: str) -> None:
        req = urllib.request.Request(f"{url}{path}", headers={
            "apikey": key, "Authorization": f"Bearer {key}",
            "Content-Profile": "platform",
            "User-Agent": "FactoryFactory/0.1 (+https://github.com/)",
        }, method="DELETE")
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
