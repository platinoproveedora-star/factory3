"""Reset de password. action=request|confirm. Sin envío de correo en v1."""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta

_TOKEN_EXPIRY_HOURS = 2
_MIN_PWD_LEN        = 8


class SecurityPasswordResetService:

    def ejecutar(self, context: dict) -> dict:
        action = (context.get("action") or "request").strip()
        url = (context.get("platform_supabase_url") or
               os.getenv("PLATFORM_SUPABASE_URL", "")).rstrip("/")
        key = (context.get("platform_supabase_service_role_key") or
               os.getenv("PLATFORM_SUPABASE_SERVICE_ROLE_KEY", ""))
        if not url or not key:
            return {"ok": False, "error": "Faltan PLATFORM_SUPABASE_URL o PLATFORM_SUPABASE_SERVICE_ROLE_KEY"}

        if action == "request":
            return self._request(context, url, key)
        if action == "confirm":
            return self._confirm(context, url, key)
        return {"ok": False, "error": "action debe ser request o confirm"}

    def _request(self, context: dict, url: str, key: str) -> dict:
        email = (context.get("email") or "").strip().lower()
        if not email:
            return {"ok": False, "error": "email requerido"}

        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run", "data": {"token": "DRY-TOKEN"}}

        # Buscar usuario — responder igual si no existe (no revelar si el email está registrado)
        user = self._get_user(url, key, email)
        if not user:
            return {"ok": True, "message": "Si el email existe, recibirás instrucciones de reset",
                    "data": {"sent": False}}

        token       = secrets.token_urlsafe(32)
        token_hash  = hashlib.sha256(token.encode()).hexdigest()
        expires_at  = (datetime.now(timezone.utc) + timedelta(hours=_TOKEN_EXPIRY_HOURS)).isoformat()

        self._pg_post(url, key, "/rest/v1/password_resets", {
            "user_id":    user["id"],
            "token_hash": token_hash,
            "expires_at": expires_at,
            "used":       False,
        })

        return {
            "ok":      True,
            "message": "Token de reset generado",
            "data": {
                "token":      token,  # en v2 esto va por email; en v1 se devuelve directamente
                "expires_at": expires_at,
                "note":       "v1: token devuelto en respuesta — conectar SMTP en v2",
            },
        }

    def _confirm(self, context: dict, url: str, key: str) -> dict:
        token        = (context.get("token") or "").strip()
        new_password = (context.get("new_password") or "").strip()

        if not token:
            return {"ok": False, "error": "token requerido"}
        if len(new_password) < _MIN_PWD_LEN:
            return {"ok": False, "error": f"nueva password debe tener al menos {_MIN_PWD_LEN} caracteres"}

        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run — password no cambiada"}

        token_hash = hashlib.sha256(token.encode()).hexdigest()
        now        = datetime.now(timezone.utc).isoformat()

        qs   = (f"?token_hash=eq.{urllib.parse.quote(token_hash)}"
                f"&used=eq.false&expires_at=gte.{urllib.parse.quote(now)}"
                f"&select=id,user_id&limit=1")
        rows = self._pg_get(url, key, f"/rest/v1/password_resets{qs}")

        if not rows:
            return {"ok": False, "error": "Token inválido o expirado"}

        reset   = rows[0]
        user_id = reset["user_id"]

        try:
            from argon2 import PasswordHasher
            ph            = PasswordHasher(time_cost=2, memory_cost=65536, parallelism=2)
            password_hash = ph.hash(new_password)
        except Exception:
            return {"ok": False, "error": "Error generando hash"}

        self._pg_patch(url, key,
                       f"/rest/v1/users?id=eq.{urllib.parse.quote(user_id)}",
                       {"password_hash": password_hash})
        self._pg_patch(url, key,
                       f"/rest/v1/password_resets?id=eq.{urllib.parse.quote(reset['id'])}",
                       {"used": True})

        return {"ok": True, "message": "Password actualizada correctamente"}

    def _get_user(self, url: str, key: str, email: str) -> dict | None:
        qs   = f"?email=eq.{urllib.parse.quote(email)}&select=id&limit=1"
        rows = self._pg_get(url, key, f"/rest/v1/users{qs}")
        return rows[0] if rows else None

    def _pg_get(self, url: str, key: str, path: str) -> list:
        req = urllib.request.Request(f"{url}{path}", headers={
            "apikey": key, "Authorization": f"Bearer {key}",
            "Accept-Profile": "platform",
            "User-Agent": "FactoryFactory/0.1 (+https://github.com/)",
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _pg_post(self, url: str, key: str, path: str, row: dict) -> None:
        req = urllib.request.Request(f"{url}{path}",
            data=json.dumps(row).encode("utf-8"),
            headers={
                "apikey": key, "Authorization": f"Bearer {key}",
                "Content-Type": "application/json", "Content-Profile": "platform",
                "Prefer": "return=minimal",
                "User-Agent": "FactoryFactory/0.1 (+https://github.com/)",
            }, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()

    def _pg_patch(self, url: str, key: str, path: str, values: dict) -> None:
        req = urllib.request.Request(f"{url}{path}",
            data=json.dumps(values).encode("utf-8"),
            headers={
                "apikey": key, "Authorization": f"Bearer {key}",
                "Content-Type": "application/json", "Content-Profile": "platform",
                "Prefer": "return=minimal",
                "User-Agent": "FactoryFactory/0.1 (+https://github.com/)",
            }, method="PATCH")
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
