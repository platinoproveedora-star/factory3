"""Valida JWT de sesión. Middleware para rutas autenticadas del dashboard."""
from __future__ import annotations

import os


class SecurityUserSessionVerifyService:

    def ejecutar(self, context: dict) -> dict:
        token      = (context.get("token") or "").strip()
        jwt_secret = (context.get("platform_jwt_secret") or
                      os.getenv("PLATFORM_JWT_SECRET", "")).strip()

        if not token:
            return {"ok": False, "error": "token requerido"}
        if not jwt_secret:
            return {"ok": False, "error": "PLATFORM_JWT_SECRET requerido"}

        if context.get("dry_run"):
            return {"ok": True, "message": "dry_run", "data": {
                "user_id": "dry-run-id", "email": "dry@run.com", "modulo_code": "dry",
            }}

        try:
            import jwt as pyjwt
            payload = pyjwt.decode(token, jwt_secret, algorithms=["HS256"])
        except pyjwt.ExpiredSignatureError:
            return {"ok": False, "error": "Sesión expirada — vuelve a iniciar sesión"}
        except pyjwt.InvalidTokenError:
            return {"ok": False, "error": "Token inválido"}
        except Exception:
            return {"ok": False, "error": "Error validando sesión"}

        return {
            "ok":      True,
            "message": "Sesión válida",
            "data": {
                "user_id":     payload.get("sub", ""),
                "email":       payload.get("email", ""),
                "modulo_code": payload.get("modulo_code", ""),
                "company_id":   payload.get("company_id", ""),
                "role":         payload.get("role", ""),
                "grant_id":     payload.get("grant_id", ""),
                "plan_code":    payload.get("plan_code", ""),
                "subscription_status": payload.get("subscription_status", ""),
                "exp":         payload.get("exp"),
            },
        }
