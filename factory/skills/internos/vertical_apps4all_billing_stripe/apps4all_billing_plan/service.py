from __future__ import annotations


class Apps4AllBillingPlanService:
    def ejecutar(self, context: dict) -> dict:
        module_code = str(context.get("module_code") or context.get("modulo_code") or "").strip()
        company_id = str(context.get("company_id") or context.get("empresa_id") or "").strip()
        price_id = str(context.get("price_id") or "").strip()
        success_url = str(context.get("success_url") or "").strip()
        cancel_url = str(context.get("cancel_url") or "").strip()
        if not module_code:
            return {"ok": False, "error": "module_code requerido"}
        plan = {
            "module_code": module_code,
            "company_id": company_id or "<company_id>",
            "price_id": price_id or "<stripe_price_id>",
            "success_url": success_url or "<success_url>",
            "cancel_url": cancel_url or "<cancel_url>",
            "delegates": [
                "vertical_stripe/stripe_customer_create",
                "vertical_stripe/stripe_checkout_create",
                "vertical_stripe/stripe_webhook_handler",
                "vertical_stripe/stripe_subscription_status",
                "vertical_apps4all_marketplace/apps4all_marketplace_module_activate",
            ],
            "required_env": ["STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET", "PLATFORM_SUPABASE_URL", "PLATFORM_SUPABASE_SERVICE_ROLE_KEY"],
        }
        return {"ok": True, "data": plan}
