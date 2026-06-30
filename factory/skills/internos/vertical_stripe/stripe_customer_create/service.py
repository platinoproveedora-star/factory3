"""Crea o recupera Stripe Customer y lo vincula a la empresa en plataforma."""
from __future__ import annotations
import json
import os
import urllib.request


class StripeCustomerCreateService:

    def ejecutar(self, context: dict) -> dict:
        company_id   = str(context.get("company_id") or "").strip()
        email        = str(context.get("email") or "").strip()
        company_name = str(context.get("company_name") or company_id).strip()
        dry_run      = context.get("dry_run", True)

        if not company_id:
            return {"ok": False, "error": "company_id requerido"}
        if not email:
            return {"ok": False, "error": "email requerido"}

        if dry_run:
            return {"ok": True, "message": "dry_run", "data": {"company_id": company_id, "email": email}}

        try:
            existing_id = self._get_existing_customer_id(company_id)
            if existing_id:
                return {"ok": True, "message": "Customer ya existe", "data": {"stripe_customer_id": existing_id, "company_id": company_id}}

            customer = self._stripe_create_customer(email, company_name, company_id)
            stripe_id = customer["id"]
            self._save_customer_id(company_id, stripe_id)

            return {"ok": True, "message": "Customer creado en Stripe", "data": {"stripe_customer_id": stripe_id, "company_id": company_id}}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _stripe_key(self) -> str:
        key = os.getenv("STRIPE_SECRET_KEY", "")
        if not key:
            raise RuntimeError("STRIPE_SECRET_KEY no configurada")
        return key

    def _stripe_post(self, path: str, params: dict) -> dict:
        body = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items()).encode()
        req = urllib.request.Request(
            f"https://api.stripe.com/v1/{path}",
            data=body,
            headers={"Authorization": f"Bearer {self._stripe_key()}", "Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())

    def _stripe_create_customer(self, email: str, name: str, company_id: str) -> dict:
        import urllib.parse
        body = f"email={urllib.parse.quote(email)}&name={urllib.parse.quote(name)}&metadata[company_id]={urllib.parse.quote(company_id)}"
        req = urllib.request.Request(
            "https://api.stripe.com/v1/customers",
            data=body.encode(),
            headers={"Authorization": f"Bearer {self._stripe_key()}", "Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())

    def _platform_base(self) -> str:
        url = os.getenv("PLATFORM_SUPABASE_URL", "").rstrip("/")
        if not url:
            raise RuntimeError("PLATFORM_SUPABASE_URL no configurada")
        return f"{url}/rest/v1"

    def _platform_headers(self, write: bool = False) -> dict:
        key = os.getenv("PLATFORM_SUPABASE_SERVICE_ROLE_KEY", "")
        if not key:
            raise RuntimeError("PLATFORM_SUPABASE_SERVICE_ROLE_KEY no configurada")
        h = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        if write:
            h["Prefer"] = "return=representation"
        return h

    def _get_existing_customer_id(self, company_id: str) -> str | None:
        qs = f"company_id=eq.{company_id}&select=stripe_customer_id&limit=1"
        req = urllib.request.Request(f"{self._platform_base()}/companies?{qs}", headers=self._platform_headers())
        with urllib.request.urlopen(req, timeout=10) as r:
            rows = json.loads(r.read() or b"[]")
        return rows[0].get("stripe_customer_id") if rows else None

    def _save_customer_id(self, company_id: str, stripe_id: str) -> None:
        qs = f"company_id=eq.{company_id}"
        data = json.dumps({"stripe_customer_id": stripe_id}).encode()
        req = urllib.request.Request(
            f"{self._platform_base()}/companies?{qs}",
            data=data,
            headers=self._platform_headers(write=True),
            method="PATCH",
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            r.read()
