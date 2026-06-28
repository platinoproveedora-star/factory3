"""Registro de usuario: email + password → Argon2id hash → platform.users."""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request

_EMAIL_RE    = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_MIN_PWD_LEN = 8


class SecurityUserRegisterService:

    def ejecutar(self, context: dict) -> dict:
        modulo_code = (context.get("modulo_code") or "").strip()
        email       = (context.get("email") or "").strip().lower()
        password    = (context.get("password") or "").strip()
        confirm     = (context.get("password_confirm") or "").strip()
        nombre      = (context.get("nombre") or "").strip()

        if not modulo_code:
            return {"ok": False, "error": "modulo_code requerido"}
        if not email or not _EMAIL_RE.match(email):
            return {"ok": False, "error": "email inválido"}
        if len(password) < _MIN_PWD_LEN:
            return {"ok": False, "error": f"password debe tener al menos {_MIN_PWD_LEN} caracteres"}
        if password != confirm:
            return {"ok": False, "error": "password y password_confirm no coinciden"}

        url = (context.get("platform_supabase_url") or
               os.getenv("PLATFORM_SUPABASE_URL", "")).rstrip("/")
        key = (context.get("platform_supabase_service_role_key") or
               os.getenv("PLATFORM_SUPABASE_SERVICE_ROLE_KEY", ""))
        if not url or not key:
            return {"ok": False, "error": "Faltan PLATFORM_SUPABASE_URL o PLATFORM_SUPABASE_SERVICE_ROLE_KEY"}

        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run — usuario no creado", "data": {"email": email}}

        try:
            password_hash = self._hash_password(password)
        except Exception as e:
            return {"ok": False, "error": "Error generando hash de password"}

        row = {
            "email":         email,
            "password_hash": password_hash,
            "nombre":        nombre,
        }

        try:
            resp = self._insert_user(url, key, row)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            if e.code == 409 or "duplicate" in body.lower():
                return {"ok": False, "error": "El email ya está registrado"}
            return {"ok": False, "error": f"Supabase {e.code}: {body[:200]}"}
        except Exception as e:
            return {"ok": False, "error": "Error guardando usuario"}

        user_id = resp[0].get("id") if resp else None
        return {
            "ok":      True,
            "message": f"Usuario registrado: {email}",
            "data":    {"user_id": user_id, "email": email, "modulo_code": modulo_code},
        }

    def _hash_password(self, password: str) -> str:
        from argon2 import PasswordHasher
        ph = PasswordHasher(time_cost=2, memory_cost=65536, parallelism=2)
        return ph.hash(password)

    def _insert_user(self, url: str, key: str, row: dict) -> list:
        req = urllib.request.Request(
            f"{url}/rest/v1/users",
            data=json.dumps(row).encode("utf-8"),
            headers={
                "apikey":          key,
                "Authorization":   f"Bearer {key}",
                "Content-Type":    "application/json",
                "Content-Profile": "platform",
                "Prefer":          "return=representation",
                "User-Agent":      "FactoryFactory/0.1 (+https://github.com/)",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
