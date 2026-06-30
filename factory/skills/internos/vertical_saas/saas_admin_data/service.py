"""Datos para panel admin: empresas, módulos activos, estado Stripe."""
from __future__ import annotations
import json
import os
import urllib.request


class SaasAdminDataService:

    def ejecutar(self, context: dict) -> dict:
        try:
            companies = self._get_companies()
            grants    = self._get_grants()

            grants_by_company: dict = {}
            for g in grants:
                cid = g.get("company_id", "")
                grants_by_company.setdefault(cid, []).append({
                    "modulo_code": g.get("modulo_code"),
                    "plan": g.get("plan"),
                    "activo": g.get("activo"),
                    "stripe_subscription_id": g.get("stripe_subscription_id"),
                })

            result = []
            for c in companies:
                cid = c.get("company_id", "")
                result.append({
                    "company_id": cid,
                    "name": c.get("name"),
                    "plan": c.get("plan"),
                    "status": c.get("status"),
                    "stripe_customer_id": c.get("stripe_customer_id"),
                    "modulos": grants_by_company.get(cid, []),
                    "created_at": c.get("created_at"),
                })

            activas   = sum(1 for c in result if c["status"] == "active")
            con_stripe = sum(1 for c in result if c.get("stripe_customer_id"))

            return {
                "ok": True,
                "data": {
                    "empresas": result,
                    "resumen": {
                        "total": len(result),
                        "activas": activas,
                        "con_stripe": con_stripe,
                    },
                },
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _headers(self) -> dict:
        key = os.getenv("PLATFORM_SUPABASE_SERVICE_ROLE_KEY", "")
        if not key:
            raise RuntimeError("PLATFORM_SUPABASE_SERVICE_ROLE_KEY no configurada")
        return {"apikey": key, "Authorization": f"Bearer {key}"}

    def _base(self) -> str:
        url = os.getenv("PLATFORM_SUPABASE_URL", "").rstrip("/")
        if not url:
            raise RuntimeError("PLATFORM_SUPABASE_URL no configurada")
        return f"{url}/rest/v1"

    def _get(self, path: str) -> list:
        req = urllib.request.Request(f"{self._base()}/{path}", headers=self._headers())
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read() or b"[]")

    def _get_companies(self) -> list:
        return self._get("companies?select=company_id,name,plan,status,stripe_customer_id,created_at&order=created_at.desc&limit=500")

    def _get_grants(self) -> list:
        return self._get("access_grants?select=company_id,modulo_code,plan,activo,stripe_subscription_id&limit=2000")
