from __future__ import annotations

import importlib.util
from pathlib import Path


class Apps4AllBillingStatusService:
    def ejecutar(self, context: dict) -> dict:
        company_id = str(context.get("company_id") or context.get("empresa_id") or "").strip()
        if not company_id:
            return {"ok": False, "error": "company_id requerido"}
        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run", "data": {"delegate": "vertical_stripe/stripe_subscription_status", "company_id": company_id}}
        if context.get("confirm_billing_status") is not True:
            return {"ok": False, "error": "confirm_billing_status=true requerido para consulta real"}
        service_file = Path(__file__).resolve().parents[5] / "factory" / "skills" / "internos" / "vertical_stripe" / "stripe_subscription_status" / "service.py"
        spec = importlib.util.spec_from_file_location("_apps4all_stripe_status_service", service_file)
        if spec is None or spec.loader is None:
            return {"ok": False, "error": "stripe status base no disponible"}
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.StripeSubscriptionStatusService().ejecutar({"company_id": company_id})
