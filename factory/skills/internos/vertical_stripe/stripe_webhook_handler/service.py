"""Procesa eventos de Stripe webhook y activa/desactiva grants."""
from __future__ import annotations
import hashlib
import hmac
import json
import os
import sys
import time


_ACTIVATE_EVENTS   = {"checkout.session.completed", "invoice.payment_succeeded"}
_DEACTIVATE_EVENTS = {"customer.subscription.deleted", "invoice.payment_failed"}


class StripeWebhookHandlerService:

    def ejecutar(self, context: dict) -> dict:
        payload   = context.get("payload", "")
        signature = context.get("stripe_signature", "")
        dry_run   = context.get("dry_run", True)

        if not payload:
            return {"ok": False, "error": "payload requerido (raw body del webhook)"}

        try:
            event = self._verify_and_parse(payload, signature)
        except Exception as exc:
            return {"ok": False, "error": f"firma inválida: {exc}"}

        event_type = event.get("type", "")
        data_obj   = event.get("data", {}).get("object", {})
        metadata   = data_obj.get("metadata", {}) or data_obj.get("subscription_data", {}).get("metadata", {})
        company_id  = metadata.get("company_id", "")
        modulo_code = metadata.get("modulo_code", "gastos")

        if not company_id:
            return {"ok": True, "message": f"evento {event_type} ignorado (sin company_id en metadata)"}

        if dry_run:
            return {"ok": True, "message": "dry_run", "data": {"event_type": event_type, "company_id": company_id, "modulo_code": modulo_code}}

        if event_type in _ACTIVATE_EVENTS:
            return self._activate(company_id, modulo_code, event_type)
        if event_type in _DEACTIVATE_EVENTS:
            return self._deactivate(company_id, modulo_code, event_type)

        return {"ok": True, "message": f"evento {event_type} no requiere acción"}

    def _verify_and_parse(self, payload: str, signature: str) -> dict:
        secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
        if secret and signature:
            parts = {p.split("=")[0]: p.split("=")[1] for p in signature.split(",") if "=" in p}
            ts    = parts.get("t", "0")
            v1    = parts.get("v1", "")
            signed = f"{ts}.{payload}"
            expected = hmac.new(secret.encode(), signed.encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected, v1):
                raise ValueError("firma no coincide")
            if abs(int(time.time()) - int(ts)) > 300:
                raise ValueError("webhook expirado (>5 min)")
        return json.loads(payload)

    def _run_skill(self, skill_name: str, context: dict) -> dict:
        factory3_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".."))
        skill_path = os.path.join(factory3_root, "factory", "skills", "internos", skill_name)
        sys.path.insert(0, skill_path)
        try:
            import importlib
            mod = importlib.import_module("skill")
            importlib.reload(mod)
            return mod.run(context)
        finally:
            sys.path.pop(0)

    def _activate(self, company_id: str, modulo_code: str, event_type: str) -> dict:
        result = self._run_skill("vertical_saas/saas_grants_activate", {
            "company_id": company_id,
            "modulo_code": modulo_code,
            "plan": "active",
            "dry_run": False,
        })
        return {**result, "event_type": event_type}

    def _deactivate(self, company_id: str, modulo_code: str, event_type: str) -> dict:
        result = self._run_skill("vertical_saas/saas_grants_deactivate", {
            "company_id": company_id,
            "modulo_code": modulo_code,
            "motivo": event_type,
            "dry_run": False,
        })
        return {**result, "event_type": event_type}
