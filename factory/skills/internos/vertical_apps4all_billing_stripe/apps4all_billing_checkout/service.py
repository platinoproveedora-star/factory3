from __future__ import annotations

import importlib.util
from pathlib import Path


class Apps4AllBillingCheckoutService:
    def ejecutar(self, context: dict) -> dict:
        module_code = str(context.get("module_code") or context.get("modulo_code") or "").strip()
        if not module_code:
            return {"ok": False, "error": "module_code requerido"}
        ctx = {**context, "modulo_code": module_code}
        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run", "data": {"delegate": "vertical_stripe/stripe_checkout_create", "context": self._public_context(ctx)}}
        if context.get("confirm_billing") is not True:
            return {"ok": False, "error": "confirm_billing=true requerido para checkout real"}
        return self._stripe_checkout(Path(__file__).resolve().parents[5], ctx)

    def _stripe_checkout(self, repo_root: Path, context: dict) -> dict:
        service_file = repo_root / "factory" / "skills" / "internos" / "vertical_stripe" / "stripe_checkout_create" / "service.py"
        spec = importlib.util.spec_from_file_location("_apps4all_stripe_checkout_service", service_file)
        if spec is None or spec.loader is None:
            return {"ok": False, "error": "stripe checkout base no disponible"}
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.StripeCheckoutCreateService().ejecutar(context)

    def _public_context(self, context: dict) -> dict:
        return {key: value for key, value in context.items() if "secret" not in key.lower() and "key" not in key.lower()}
