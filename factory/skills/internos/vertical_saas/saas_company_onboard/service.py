"""Onboarding completo de empresa nueva en la plataforma SaaS."""
from __future__ import annotations
import json
import os
import urllib.request
import uuid


_DEFAULT_MODULES_SEED = {
    "gastos": "vertical_gastos4all/gastos4all_categories_seed",
}

_PLATFORM_SCHEMA = "public"


class SaasCompanyOnboardService:

    def ejecutar(self, context: dict) -> dict:
        dry_run = context.get("dry_run", True)

        company_id   = str(context.get("company_id") or "").strip()
        company_name = str(context.get("company_name") or "").strip()
        email        = str(context.get("email") or "").strip()
        password     = str(context.get("password") or "").strip()
        modules      = context.get("modules", ["gastos"])
        plan         = str(context.get("plan") or "starter").strip()

        if not company_id:
            return {"ok": False, "error": "company_id requerido"}
        if not company_name:
            return {"ok": False, "error": "company_name requerido"}
        if not email:
            return {"ok": False, "error": "email requerido"}
        if not password:
            return {"ok": False, "error": "password requerido"}

        if dry_run:
            return {
                "ok": True,
                "message": "dry_run — nada creado",
                "data": {
                    "company_id": company_id,
                    "email": email,
                    "modules": modules,
                    "plan": plan,
                },
            }

        try:
            self._create_company(company_id, company_name, plan)
        except Exception as exc:
            return {"ok": False, "error": f"create_company: {exc}"}

        try:
            user_id = self._create_user(company_id, email, password)
        except Exception as exc:
            return {"ok": False, "error": f"create_user: {exc}"}

        activated = []
        for modulo in modules:
            try:
                self._activate_grant(company_id, modulo, plan)
                activated.append(modulo)
            except Exception as exc:
                return {"ok": False, "error": f"grant {modulo}: {exc}", "activated": activated}

        return {
            "ok": True,
            "message": "Empresa creada y módulos activados",
            "data": {
                "company_id": company_id,
                "user_id": user_id,
                "email": email,
                "modules": activated,
                "plan": plan,
            },
        }

    def _platform_headers(self, write: bool = False) -> dict:
        key = os.getenv("PLATFORM_SUPABASE_SERVICE_ROLE_KEY", "")
        if not key:
            raise RuntimeError("PLATFORM_SUPABASE_SERVICE_ROLE_KEY no configurada")
        h = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }
        if write:
            h["Prefer"] = "return=representation"
        return h

    def _platform_url(self, path: str) -> str:
        base = os.getenv("PLATFORM_SUPABASE_URL", "").rstrip("/")
        if not base:
            raise RuntimeError("PLATFORM_SUPABASE_URL no configurada")
        return f"{base}/rest/v1/{path}"

    def _post(self, path: str, body: dict) -> dict:
        data = json.dumps(body).encode()
        req = urllib.request.Request(
            self._platform_url(path),
            data=data,
            headers=self._platform_headers(write=True),
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read() or b"[]")

    def _create_company(self, company_id: str, company_name: str, plan: str) -> None:
        self._post("companies", {
            "company_id": company_id,
            "name": company_name,
            "plan": plan,
            "status": "active",
        })

    def _create_user(self, company_id: str, email: str, password: str) -> str:
        import hashlib, secrets
        salt = secrets.token_hex(16)
        pw_hash = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
        user_id = str(uuid.uuid4())
        self._post("security_user_login", {
            "id": user_id,
            "company_id": company_id,
            "email": email,
            "password_hash": pw_hash,
            "password_salt": salt,
            "role": "admin",
            "activo": True,
        })
        return user_id

    def _activate_grant(self, company_id: str, modulo_code: str, plan: str) -> None:
        self._post("access_grants", {
            "company_id": company_id,
            "modulo_code": modulo_code,
            "plan": plan,
            "activo": True,
        })
