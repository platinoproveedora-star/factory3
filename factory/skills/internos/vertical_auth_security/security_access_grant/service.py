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
        company_id  = (context.get("company_id") or context.get("empresa_id") or "").strip()

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
            return self._create(context, url, key, user_id, modulo_code, company_id)
        if action == "check":
            return self._check(url, key, user_id, modulo_code, company_id)
        if action == "delete":
            return self._delete(context, url, key, user_id, modulo_code, company_id)
        return {"ok": False, "error": f"action inválido: {action}. Usa create|check|delete"}

    def _create(self, context: dict, url: str, key: str, user_id: str, modulo_code: str, company_id: str = "") -> dict:
        role = (context.get("role") or "owner").strip()
        if role not in ("owner", "admin", "operator", "viewer", "platform_admin"):
            return {"ok": False, "error": "role debe ser owner, admin, operator, viewer o platform_admin"}

        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run — grant no creado", "data": {
                "user_id": user_id, "company_id": company_id, "modulo_code": modulo_code, "role": role,
            }}

        try:
            row = {
                "user_id":     user_id,
                "modulo_code": modulo_code,
                "role":        role,
                "status":      context.get("status") or "manual",
                "plan_code":   context.get("plan_code") or f"{modulo_code}_manual",
                "subscription_status": context.get("subscription_status") or "manual",
            }
            if company_id:
                row["company_id"] = company_id
            rows = self._pg_post(url, key, row)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            return self._handle_create_conflict(e.code, body, modulo_code)

        grant_id = rows[0].get("id") if rows else None
        return {
            "ok":      True,
            "message": f"Acceso otorgado a '{modulo_code}' para user {user_id}",
            "data":    {"grant_id": grant_id, "user_id": user_id, "company_id": company_id, "modulo_code": modulo_code, "role": role},
        }

    def _handle_create_conflict(self, status_code: int, body: str, modulo_code: str) -> dict:
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = {}
        pg_code = str(parsed.get("code") or "")
        pg_message = str(parsed.get("message") or "")
        pg_details = str(parsed.get("details") or "")

        if pg_code == "23505":
            return {"ok": True, "message": "Grant ya existe", "data": {"created": False}}
        if pg_code == "23503":
            return {"ok": False, "error": f"modulo_code '{modulo_code}' no existe en platform.modulos (foreign key violation): {pg_details or pg_message}"}
        if status_code == 409:
            return {"ok": False, "error": f"Supabase 409 no identificado: {pg_message or body[:200]}"}
        return {"ok": False, "error": f"Supabase {status_code}: {body[:200]}"}

    def _check(self, url: str, key: str, user_id: str, modulo_code: str, company_id: str = "") -> dict:
        qs   = (f"?user_id=eq.{urllib.parse.quote(user_id)}"
                f"&modulo_code=eq.{urllib.parse.quote(modulo_code)}"
                f"&select=id,role,company_id,status,plan_code,subscription_status&limit=5")
        if company_id:
            qs += f"&company_id=eq.{urllib.parse.quote(company_id)}"
        rows = self._pg_get(url, key, f"/rest/v1/access_grants{qs}")
        active_statuses = {"active", "trialing", "manual", "comped"}
        active = [
            row for row in rows
            if str(row.get("status") or "manual") in active_statuses
            and str(row.get("subscription_status") or row.get("status") or "manual") in active_statuses
        ]
        has  = bool(active)
        return {
            "ok":      True,
            "message": f"Acceso {'concedido' if has else 'denegado'} a '{modulo_code}'",
            "data":    {"has_access": has, "grant": active[0] if has else None, "role": active[0].get("role") if has else None},
        }

    def _delete(self, context: dict, url: str, key: str, user_id: str, modulo_code: str, company_id: str = "") -> dict:
        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run — grant no eliminado"}
        qs = (f"?user_id=eq.{urllib.parse.quote(user_id)}"
              f"&modulo_code=eq.{urllib.parse.quote(modulo_code)}")
        if company_id:
            qs += f"&company_id=eq.{urllib.parse.quote(company_id)}"
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
