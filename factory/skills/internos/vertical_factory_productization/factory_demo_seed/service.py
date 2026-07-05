from __future__ import annotations

import re
from typing import Any

from factory.engine import SupabaseClient


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
COMPANY_RE = re.compile(r"^EMP_[A-Z0-9_]+$")
MODULE_RE = re.compile(r"^[a-z][a-z0-9_]*$")


class FactoryDemoSeedService:
    def ejecutar(self, context: dict) -> dict:
        company_id = str(context.get("company_id") or context.get("empresa_id") or "").strip().upper()
        company_name = str(context.get("company_name") or company_id).strip()
        email = str(context.get("email") or "").strip().lower()
        password = str(context.get("password") or "").strip()
        modules = context.get("modules") or context.get("module_codes") or []
        if isinstance(modules, str):
            modules = [modules]
        modules = [str(item).strip() for item in modules if str(item).strip()]
        role = str(context.get("role") or "owner").strip()

        errors = self._validate(company_id, company_name, email, password, modules)
        if errors:
            return {"ok": False, "error": "; ".join(errors)}

        planned = {
            "company": {"company_id": company_id, "name": company_name, "status": "active"},
            "user": {"email": email, "nombre": context.get("nombre") or company_name},
            "grants": [{"company_id": company_id, "modulo_code": module_code, "role": role} for module_code in modules],
        }
        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run", "data": planned}

        db = SupabaseClient({"schema": "platform"})
        company_result = db.rest_upsert("companies", planned["company"], "company_id")
        if not company_result.get("ok"):
            return company_result

        user = self._find_user(db, email)
        created_user = False
        if not user:
            user_result = self._create_user(db, email, password, str(context.get("nombre") or company_name))
            if not user_result.get("ok"):
                return user_result
            user = (user_result.get("data") or [{}])[0]
            created_user = True

        user_id = user.get("id")
        if not user_id:
            return {"ok": False, "error": "user_id no resuelto"}

        company_user = {
            "company_id": company_id,
            "user_id": user_id,
            "role": role,
            "status": "active",
        }
        company_user_result = db.rest_upsert("company_users", company_user, "company_id,user_id")
        if not company_user_result.get("ok"):
            return company_user_result

        grant_rows = [
            {
                "user_id": user_id,
                "company_id": company_id,
                "modulo_code": module_code,
                "role": role,
                "status": "manual",
                "plan_code": f"{module_code}_demo",
                "subscription_status": "manual",
                "metadata": {"seed": "factory_demo_seed"},
            }
            for module_code in modules
        ]
        grants_result = db.rest_upsert("access_grants", grant_rows, "user_id,company_id,modulo_code")
        if not grants_result.get("ok"):
            return grants_result

        return {
            "ok": True,
            "message": "demo seed ready",
            "data": {
                "company_id": company_id,
                "user_id": user_id,
                "email": email,
                "created_user": created_user,
                "modules": modules,
                "grants": grants_result.get("data") or [],
            },
        }

    def _validate(self, company_id: str, company_name: str, email: str, password: str, modules: list[str]) -> list[str]:
        errors = []
        if not COMPANY_RE.match(company_id):
            errors.append("company_id requerido con formato EMP_...")
        if not company_name:
            errors.append("company_name requerido")
        if not EMAIL_RE.match(email):
            errors.append("email invalido")
        if len(password) < 8:
            errors.append("password minimo 8 caracteres")
        if not modules:
            errors.append("modules requerido")
        for module_code in modules:
            if not MODULE_RE.match(module_code):
                errors.append(f"module_code invalido: {module_code}")
        return errors

    def _find_user(self, db: SupabaseClient, email: str) -> dict[str, Any] | None:
        result = db.rest_select("users", {"email": email}, select="id,email,nombre", limit=1)
        if result.get("ok") and result.get("data"):
            return result["data"][0]
        return None

    def _create_user(self, db: SupabaseClient, email: str, password: str, nombre: str) -> dict:
        password_hash = self._hash_password(password)
        return db.rest_insert("users", {"email": email, "password_hash": password_hash, "nombre": nombre})

    def _hash_password(self, password: str) -> str:
        from argon2 import PasswordHasher

        return PasswordHasher(time_cost=2, memory_cost=65536, parallelism=2).hash(password)
