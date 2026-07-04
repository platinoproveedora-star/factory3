from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from typing import Any


ALLOWED_COMPANY_ID = os.getenv("APPS4ALL_ALLOWED_COMPANY_ID", "EMP_APPS4ALL")

_PLATFORM_SCHEMA = "platform"


class PlatformAccountInspectService:

    def ejecutar(self, context: dict) -> dict:
        company_id = str(context.get("company_id") or os.getenv("APPS4ALL_ALLOWED_COMPANY_ID", "")).strip()
        if not company_id:
            return {"ok": False, "error": "company_id requerido"}
        if company_id != ALLOWED_COMPANY_ID:
            return {
                "ok": False,
                "error": f"company_id no autorizado para este skill; esperado={ALLOWED_COMPANY_ID}",
            }
        try:
            company = self._company(company_id)
            users = self._users(company_id)
            grants = self._grants(company_id)
            return {
                "ok": True,
                "data": {
                    "schema": _PLATFORM_SCHEMA,
                    "company_id": company_id,
                    "company": company,
                    "users": users,
                    "access_grants": grants,
                },
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _headers(self) -> dict:
        key = os.getenv("PLATFORM_SUPABASE_SERVICE_ROLE_KEY", "")
        if not key:
            raise RuntimeError("PLATFORM_SUPABASE_SERVICE_ROLE_KEY no configurada")
        return {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Accept": "application/json",
            "Accept-Profile": _PLATFORM_SCHEMA,
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    def _platform_rest_url(self) -> str:
        url = os.getenv("PLATFORM_SUPABASE_URL", "").rstrip("/")
        if not url:
            raise RuntimeError("PLATFORM_SUPABASE_URL no configurada")
        return f"{url}/rest/v1"

    def _get(self, path: str) -> Any:
        req = urllib.request.Request(f"{self._platform_rest_url()}/{path}", headers=self._headers())
        with urllib.request.urlopen(req, timeout=20) as r:
            body = r.read() or b"[]"
            return json.loads(body)

    def _company(self, company_id: str) -> dict | None:
        rows = self._get(f"companies?select=company_id,name,plan,status,stripe_customer_id,created_at&company_id=eq.{urllib.parse.quote(company_id)}&limit=1")
        return rows[0] if isinstance(rows, list) and rows else None

    def _users(self, company_id: str) -> list[dict[str, Any]]:
        return self._get(f"users?select=id,email,role,company_id,activo,created_at&company_id=eq.{urllib.parse.quote(company_id)}&order=created_at.desc&limit=500")

    def _grants(self, company_id: str) -> list[dict[str, Any]]:
        return self._get(f"access_grants?select=user_id,modulo_code,plan,activo,stripe_subscription_id,created_at&company_id=eq.{urllib.parse.quote(company_id)}&order=created_at.desc&limit=500")
