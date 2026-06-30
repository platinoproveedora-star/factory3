"""Consulta estado de suscripción Stripe para una empresa."""
from __future__ import annotations
import json
import os
import urllib.request


class StripeSubscriptionStatusService:

    def ejecutar(self, context: dict) -> dict:
        company_id = str(context.get("company_id") or "").strip()
        if not company_id:
            return {"ok": False, "error": "company_id requerido"}

        try:
            company = self._get_company(company_id)
            if not company:
                return {"ok": False, "error": f"empresa {company_id} no encontrada"}

            stripe_customer_id = company.get("stripe_customer_id")
            if not stripe_customer_id:
                return {"ok": True, "data": {"company_id": company_id, "stripe_customer_id": None, "subscriptions": [], "status": "no_stripe"}}

            subs = self._get_subscriptions(stripe_customer_id)
            grants = self._get_grants(company_id)

            return {
                "ok": True,
                "data": {
                    "company_id": company_id,
                    "stripe_customer_id": stripe_customer_id,
                    "subscriptions": subs,
                    "grants_activos": [g["modulo_code"] for g in grants if g.get("activo")],
                    "status": subs[0]["status"] if subs else "no_subscription",
                },
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _stripe_key(self) -> str:
        key = os.getenv("STRIPE_SECRET_KEY", "")
        if not key:
            raise RuntimeError("STRIPE_SECRET_KEY no configurada")
        return key

    def _platform_base(self) -> str:
        url = os.getenv("PLATFORM_SUPABASE_URL", "").rstrip("/")
        if not url:
            raise RuntimeError("PLATFORM_SUPABASE_URL no configurada")
        return f"{url}/rest/v1"

    def _platform_headers(self) -> dict:
        key = os.getenv("PLATFORM_SUPABASE_SERVICE_ROLE_KEY", "")
        if not key:
            raise RuntimeError("PLATFORM_SUPABASE_SERVICE_ROLE_KEY no configurada")
        return {"apikey": key, "Authorization": f"Bearer {key}"}

    def _get_company(self, company_id: str) -> dict | None:
        qs = f"company_id=eq.{company_id}&select=company_id,name,plan,stripe_customer_id&limit=1"
        req = urllib.request.Request(f"{self._platform_base()}/companies?{qs}", headers=self._platform_headers())
        with urllib.request.urlopen(req, timeout=10) as r:
            rows = json.loads(r.read() or b"[]")
        return rows[0] if rows else None

    def _get_grants(self, company_id: str) -> list:
        qs = f"company_id=eq.{company_id}&select=modulo_code,plan,activo&limit=50"
        req = urllib.request.Request(f"{self._platform_base()}/access_grants?{qs}", headers=self._platform_headers())
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read() or b"[]")

    def _get_subscriptions(self, customer_id: str) -> list:
        qs = f"customer={customer_id}&limit=5"
        req = urllib.request.Request(
            f"https://api.stripe.com/v1/subscriptions?{qs}",
            headers={"Authorization": f"Bearer {self._stripe_key()}"},
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
        return [{"id": s["id"], "status": s["status"], "current_period_end": s.get("current_period_end"), "items": [i["price"]["id"] for i in s.get("items", {}).get("data", [])]} for s in data.get("data", [])]
