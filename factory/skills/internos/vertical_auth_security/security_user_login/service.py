"""Login: email+password → JWT. Throttling por email+IP. Bloqueo tras 5 fallos consecutivos."""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone, timedelta

_MAX_ATTEMPTS  = 5
_LOCKOUT_MIN   = 15
_JWT_EXP_HOURS = 2
_EMAIL_RE      = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class SecurityUserLoginService:

    def ejecutar(self, context: dict) -> dict:
        modulo_code = (context.get("modulo_code") or "").strip()
        company_id  = (context.get("company_id") or context.get("empresa_id") or "").strip()
        email       = (context.get("email") or "").strip().lower()
        password    = (context.get("password") or "").strip()
        ip          = (context.get("ip") or "unknown").strip()

        if not modulo_code:
            return {"ok": False, "error": "modulo_code requerido"}
        if not email or not _EMAIL_RE.match(email):
            return {"ok": False, "error": "email inválido"}
        if not password:
            return {"ok": False, "error": "password requerido"}

        url = (context.get("platform_supabase_url") or
               os.getenv("PLATFORM_SUPABASE_URL", "")).rstrip("/")
        key = (context.get("platform_supabase_service_role_key") or
               os.getenv("PLATFORM_SUPABASE_SERVICE_ROLE_KEY", ""))
        jwt_secret = (context.get("platform_jwt_secret") or
                      os.getenv("PLATFORM_JWT_SECRET", "")).strip()

        if not url or not key:
            return {"ok": False, "error": "Faltan PLATFORM_SUPABASE_URL o PLATFORM_SUPABASE_SERVICE_ROLE_KEY"}
        if not jwt_secret:
            return {"ok": False, "error": "PLATFORM_JWT_SECRET requerido"}

        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run", "data": {"token": "DRY-RUN-JWT"}}

        # 1 — Verificar throttling
        locked, reason = self._check_throttle(url, key, email, ip)
        if locked:
            self._log_attempt(url, key, email, ip, success=False)
            return {"ok": False, "error": reason}

        # 2 — Buscar usuario
        user = self._get_user(url, key, email)
        if not user:
            self._log_attempt(url, key, email, ip, success=False)
            return {"ok": False, "error": "Credenciales incorrectas"}

        # 3 — Verificar password
        try:
            valid = self._verify_password(password, user["password_hash"])
        except Exception:
            self._log_attempt(url, key, email, ip, success=False)
            return {"ok": False, "error": "Credenciales incorrectas"}

        if not valid:
            self._log_attempt(url, key, email, ip, success=False)
            return {"ok": False, "error": "Credenciales incorrectas"}

        # 4 — Verificar acceso al módulo
        grant = self._check_access(url, key, user["id"], modulo_code, company_id)
        if not grant:
            self._log_attempt(url, key, email, ip, success=False)
            return {"ok": False, "error": f"Sin acceso al módulo '{modulo_code}'"}

        # 5 — Generar JWT
        self._log_attempt(url, key, email, ip, success=True)
        token = self._generate_jwt(user["id"], email, modulo_code, jwt_secret, grant)

        return {
            "ok":      True,
            "message": f"Login exitoso: {email}",
            "data": {
                "token":       token,
                "user_id":     user["id"],
                "email":       email,
                "nombre":      user.get("nombre", ""),
                "modulo_code": modulo_code,
                "company_id":   grant.get("company_id", ""),
                "role":         grant.get("role", ""),
                "grant_id":     grant.get("id", ""),
                "plan_code":    grant.get("plan_code") or "",
                "subscription_status": grant.get("subscription_status") or grant.get("status") or "",
                "expires_in":  _JWT_EXP_HOURS * 3600,
            },
        }

    # ── helpers ──────────────────────────────────────────────────────────────

    def _check_throttle(self, url: str, key: str, email: str, ip: str) -> tuple[bool, str]:
        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=_LOCKOUT_MIN)).isoformat()
        for field, value in [("email", email), ("ip", ip)]:
            try:
                qs   = f"?{field}=eq.{urllib.parse.quote(value)}&success=eq.false&created_at=gte.{cutoff}&select=id&limit={_MAX_ATTEMPTS + 1}"
                rows = self._pg_get(url, key, f"/rest/v1/login_attempts{qs}")
                if len(rows) >= _MAX_ATTEMPTS:
                    return True, f"Demasiados intentos fallidos. Espera {_LOCKOUT_MIN} minutos."
            except Exception:
                pass
        return False, ""

    def _log_attempt(self, url: str, key: str, email: str, ip: str, success: bool) -> None:
        try:
            self._pg_post(url, key, "/rest/v1/login_attempts", {
                "email": email, "ip": ip, "success": success,
            })
        except Exception:
            pass

    def _get_user(self, url: str, key: str, email: str) -> dict | None:
        import urllib.parse
        qs   = f"?email=eq.{urllib.parse.quote(email)}&select=id,email,password_hash,nombre&limit=1"
        rows = self._pg_get(url, key, f"/rest/v1/users{qs}")
        return rows[0] if rows else None

    def _verify_password(self, password: str, password_hash: str) -> bool:
        from argon2 import PasswordHasher
        from argon2.exceptions import VerifyMismatchError
        ph = PasswordHasher()
        try:
            ph.verify(password_hash, password)
            return True
        except VerifyMismatchError:
            return False

    def _check_access(self, url: str, key: str, user_id: str, modulo_code: str, company_id: str = "") -> dict | None:
        import urllib.parse
        qs   = (f"?user_id=eq.{user_id}"
                f"&modulo_code=eq.{urllib.parse.quote(modulo_code)}"
                f"&select=id,user_id,company_id,modulo_code,role,status,plan_code,subscription_status&limit=5")
        if company_id:
            qs += f"&company_id=eq.{urllib.parse.quote(company_id)}"
        rows = self._pg_get(url, key, f"/rest/v1/access_grants{qs}")
        active_statuses = {"active", "trialing", "manual", "comped"}
        active = [
            row for row in rows
            if str(row.get("status") or "manual") in active_statuses
            and str(row.get("subscription_status") or row.get("status") or "manual") in active_statuses
        ]
        return active[0] if active else None

    def _generate_jwt(self, user_id: str, email: str, modulo_code: str, secret: str, grant: dict | None = None) -> str:
        import jwt
        now     = datetime.now(timezone.utc)
        grant = grant or {}
        payload = {
            "sub":         user_id,
            "email":       email,
            "modulo_code": modulo_code,
            "company_id":   grant.get("company_id", ""),
            "role":         grant.get("role", ""),
            "grant_id":     grant.get("id", ""),
            "plan_code":    grant.get("plan_code") or "",
            "subscription_status": grant.get("subscription_status") or grant.get("status") or "",
            "iat":         int(now.timestamp()),
            "exp":         int((now + timedelta(hours=_JWT_EXP_HOURS)).timestamp()),
        }
        return jwt.encode(payload, secret, algorithm="HS256")

    def _pg_get(self, url: str, key: str, path: str) -> list:
        req = urllib.request.Request(
            f"{url}{path}",
            headers={
                "apikey":         key,
                "Authorization":  f"Bearer {key}",
                "Accept-Profile": "platform",
                "User-Agent":     "FactoryFactory/0.1 (+https://github.com/)",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _pg_post(self, url: str, key: str, path: str, row: dict) -> None:
        req = urllib.request.Request(
            f"{url}{path}",
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
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()


import urllib.parse
