"""Activa acceso a un módulo para una empresa en access_grants."""
from __future__ import annotations
import json
import os
import urllib.request


class SaasGrantsActivateService:

    def ejecutar(self, context: dict) -> dict:
        company_id   = str(context.get("company_id") or "").strip()
        modulo_code  = str(context.get("modulo_code") or "").strip()
        plan         = str(context.get("plan") or "starter").strip()
        dry_run      = context.get("dry_run", True)

        if not company_id:
            return {"ok": False, "error": "company_id requerido"}
        if not modulo_code:
            return {"ok": False, "error": "modulo_code requerido"}

        if dry_run:
            return {"ok": True, "message": "dry_run", "data": {"company_id": company_id, "modulo_code": modulo_code}}

        try:
            existing = self._get_grant(company_id, modulo_code)
            if existing:
                self._patch_grant(company_id, modulo_code, {"activo": True, "plan": plan})
                action = "reactivado"
            else:
                self._post_grant(company_id, modulo_code, plan)
                action = "creado"
            return {"ok": True, "message": f"Grant {action}", "data": {"company_id": company_id, "modulo_code": modulo_code, "plan": plan}}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _headers(self, write: bool = False) -> dict:
        key = os.getenv("PLATFORM_SUPABASE_SERVICE_ROLE_KEY", "")
        if not key:
            raise RuntimeError("PLATFORM_SUPABASE_SERVICE_ROLE_KEY no configurada")
        h = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        if write:
            h["Prefer"] = "return=representation"
        return h

    def _base(self) -> str:
        url = os.getenv("PLATFORM_SUPABASE_URL", "").rstrip("/")
        if not url:
            raise RuntimeError("PLATFORM_SUPABASE_URL no configurada")
        return f"{url}/rest/v1"

    def _get_grant(self, company_id: str, modulo_code: str) -> list:
        qs = f"company_id=eq.{company_id}&modulo_code=eq.{modulo_code}&select=id&limit=1"
        req = urllib.request.Request(f"{self._base()}/access_grants?{qs}", headers=self._headers())
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read() or b"[]")

    def _post_grant(self, company_id: str, modulo_code: str, plan: str) -> None:
        data = json.dumps({"company_id": company_id, "modulo_code": modulo_code, "plan": plan, "activo": True}).encode()
        req = urllib.request.Request(f"{self._base()}/access_grants", data=data, headers=self._headers(write=True), method="POST")
        with urllib.request.urlopen(req, timeout=10) as r:
            r.read()

    def _patch_grant(self, company_id: str, modulo_code: str, values: dict) -> None:
        qs = f"company_id=eq.{company_id}&modulo_code=eq.{modulo_code}"
        data = json.dumps(values).encode()
        req = urllib.request.Request(f"{self._base()}/access_grants?{qs}", data=data, headers=self._headers(write=True), method="PATCH")
        with urllib.request.urlopen(req, timeout=10) as r:
            r.read()
