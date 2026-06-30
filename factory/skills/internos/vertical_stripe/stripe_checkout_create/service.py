"""Crea sesión de Stripe Checkout para un plan/módulo."""
from __future__ import annotations
import json
import os
import urllib.parse
import urllib.request


class StripeCheckoutCreateService:

    def ejecutar(self, context: dict) -> dict:
        company_id   = str(context.get("company_id") or "").strip()
        email        = str(context.get("email") or "").strip()
        price_id     = str(context.get("price_id") or "").strip()
        modulo_code  = str(context.get("modulo_code") or "gastos").strip()
        success_url  = str(context.get("success_url") or "").strip()
        cancel_url   = str(context.get("cancel_url") or "").strip()
        dry_run      = context.get("dry_run", True)

        if not company_id:
            return {"ok": False, "error": "company_id requerido"}
        if not price_id:
            return {"ok": False, "error": "price_id requerido (Stripe Price ID)"}
        if not success_url or not cancel_url:
            return {"ok": False, "error": "success_url y cancel_url requeridos"}

        if dry_run:
            return {"ok": True, "message": "dry_run", "data": {"company_id": company_id, "price_id": price_id, "modulo_code": modulo_code}}

        try:
            params = [
                ("mode", "subscription"),
                ("customer_email", email),
                ("line_items[0][price]", price_id),
                ("line_items[0][quantity]", "1"),
                ("success_url", success_url),
                ("cancel_url", cancel_url),
                ("metadata[company_id]", company_id),
                ("metadata[modulo_code]", modulo_code),
                ("subscription_data[metadata][company_id]", company_id),
                ("subscription_data[metadata][modulo_code]", modulo_code),
            ]
            body = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params).encode()
            key = os.getenv("STRIPE_SECRET_KEY", "")
            if not key:
                return {"ok": False, "error": "STRIPE_SECRET_KEY no configurada"}

            req = urllib.request.Request(
                "https://api.stripe.com/v1/checkout/sessions",
                data=body,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/x-www-form-urlencoded"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as r:
                session = json.loads(r.read())

            return {"ok": True, "data": {"checkout_url": session["url"], "session_id": session["id"], "company_id": company_id}}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
