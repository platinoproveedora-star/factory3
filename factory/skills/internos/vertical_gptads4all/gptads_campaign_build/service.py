from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

from factory.engine import SupabaseClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gptads_common import OBJECTIVES, clean_text  # noqa: E402


class GptAdsCampaignBuildService:
    def ejecutar(self, context: dict) -> dict:
        product_brief = context.get("product_brief") if isinstance(context.get("product_brief"), dict) else {}
        intent_set = context.get("intent_set") if isinstance(context.get("intent_set"), dict) else {}
        context_hint_set = context.get("context_hint_set") if isinstance(context.get("context_hint_set"), dict) else {}

        empresa_id = clean_text(product_brief.get("empresa_id") or context.get("empresa_id") or context.get("company_id"))
        product_key = clean_text(product_brief.get("product_key"))
        if not empresa_id or not product_key:
            return {"ok": False, "error": "empresa_id and product_key required"}

        intents = intent_set.get("intents") if isinstance(intent_set.get("intents"), list) else []
        hints = context_hint_set.get("hints") if isinstance(context_hint_set.get("hints"), list) else []
        intent_ids = [clean_text(item.get("intent_id")) for item in intents if isinstance(item, dict) and clean_text(item.get("intent_id"))]
        hint_ids = [clean_text(item.get("hint_id")) for item in hints if isinstance(item, dict) and clean_text(item.get("hint_id"))]
        hint_intents = {clean_text(item.get("intent_id")) for item in hints if isinstance(item, dict)}
        if not intent_ids or not set(hint_intents).issubset(set(intent_ids)):
            return {"ok": False, "error": "invalid_intent_ids"}

        market = product_brief.get("market") if isinstance(product_brief.get("market"), dict) else {}
        country = clean_text(market.get("country")).upper()
        currency = clean_text(context.get("currency")).upper()
        if not currency:
            currency = {"MX": "MXN", "US": "USD"}.get(country, "")
        if not currency:
            return {"ok": False, "error": "currency_required"}

        objective = clean_text(context.get("objective") or "conversions").lower()
        if objective not in OBJECTIVES:
            objective = "conversions"
        budget = context.get("daily_budget_amount", 500)
        try:
            budget = float(budget)
        except Exception:
            budget = 500.0
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        campaign_key = f"camp_{product_key}_{timestamp}"
        campaign_name = f"{clean_text(product_brief.get('product_name'))} - {country or 'GEN'}"
        campaign_draft = {
            "empresa_id": empresa_id,
            "company_id": empresa_id,
            "project_code": clean_text(context.get("project_code")) or None,
            "module_code": clean_text(context.get("module_code")) or None,
            "product_id": clean_text(context.get("product_id")) or None,
            "brief_id": clean_text(context.get("brief_id")) or None,
            "product_key": product_key,
            "campaign_key": campaign_key,
            "campaign_name": campaign_name,
            "objective": objective,
            "daily_budget_amount": budget,
            "currency": currency,
            "status": "draft",
            "intent_ids": intent_ids,
            "hint_ids": hint_ids,
            "creative_angles_used": context.get("creative_angles_used") if isinstance(context.get("creative_angles_used"), list) else [],
            "brief_analysis": context.get("brief_analysis") if isinstance(context.get("brief_analysis"), dict) else None,
        }

        warnings = []
        if context.get("dry_run", True):
            return {"ok": True, "data": {"campaign_draft": campaign_draft, "warnings": warnings}}

        ctx = dict(context)
        schema = clean_text(ctx.get("schema") or ctx.get("supabase_schema") or ctx.get("db_schema"))
        if not schema:
            return {"ok": False, "error": "schema required for write"}
        ctx["schema"] = schema
        ctx["company_id"] = empresa_id
        try:
            db = SupabaseClient(ctx)
            product_row = {
                "empresa_id": empresa_id,
                "company_id": empresa_id,
                "project_code": clean_text(context.get("project_code")) or None,
                "module_code": clean_text(context.get("module_code")) or None,
                "product_key": product_key,
                "product_name": product_brief.get("product_name"),
                "description": product_brief.get("description"),
                "category": product_brief.get("category"),
                "price_range": product_brief.get("price_range"),
                "url": product_brief.get("url"),
                "market": product_brief.get("market"),
                "value_props": product_brief.get("value_props"),
                "tone": product_brief.get("tone"),
            }
            product_call = db.rest_upsert("products", product_row, "empresa_id,product_key")
            if not product_call.get("ok") and any(col in str(product_call.get("error") or "") for col in ["company_id", "project_code", "module_code"]):
                legacy_product = dict(product_row)
                for key in ("company_id", "project_code", "module_code"):
                    legacy_product.pop(key, None)
                product_call = db.rest_upsert("products", legacy_product, "empresa_id,product_key")
            campaign_call = db.rest_upsert("campaigns", campaign_draft, "empresa_id,campaign_key")
            if not campaign_call.get("ok") and any(col in str(campaign_call.get("error") or "") for col in ["company_id", "project_code", "module_code", "product_id", "brief_id", "creative_angles_used", "brief_analysis"]):
                legacy_campaign = dict(campaign_draft)
                for key in ("company_id", "project_code", "module_code", "product_id", "brief_id", "creative_angles_used", "brief_analysis"):
                    legacy_campaign.pop(key, None)
                campaign_call = db.rest_upsert("campaigns", legacy_campaign, "empresa_id,campaign_key")
            calls = [
                ("products", product_call),
                ("intents", db.rest_upsert("intents", [{**item, "empresa_id": empresa_id, "product_key": product_key} for item in intents], "empresa_id,product_key,intent_id")),
                ("context_hints", db.rest_upsert("context_hints", [{**item, "empresa_id": empresa_id, "product_key": product_key} for item in hints], "empresa_id,product_key,hint_id")),
                ("campaigns", campaign_call),
            ]
            for stage, call in calls:
                if not call.get("ok"):
                    return {"ok": False, "error": "db_persistence_failed", "data": {"stage": stage, "db_error": str(call.get("error", ""))[:500]}}
        except Exception as exc:
            return {"ok": False, "error": "db_persistence_failed", "data": {"stage": "exception", "db_error": str(exc)[:500]}}

        return {"ok": True, "data": {"campaign_draft": campaign_draft, "warnings": warnings}}
