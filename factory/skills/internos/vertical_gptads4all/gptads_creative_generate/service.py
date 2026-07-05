from __future__ import annotations

import json
import sys
from pathlib import Path

from factory.engine import SupabaseClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gptads_common import ai_json, clamp_int, clean_text, clip, seq  # noqa: E402


class GptAdsCreativeGenerateService:
    def ejecutar(self, context: dict) -> dict:
        campaign_draft = context.get("campaign_draft") if isinstance(context.get("campaign_draft"), dict) else {}
        product_brief = context.get("product_brief") if isinstance(context.get("product_brief"), dict) else {}
        intent_set = context.get("intent_set") if isinstance(context.get("intent_set"), dict) else {}
        context_hint_set = context.get("context_hint_set") if isinstance(context.get("context_hint_set"), dict) else {}
        intents = intent_set.get("intents") if isinstance(intent_set.get("intents"), list) else []
        hints = context_hint_set.get("hints") if isinstance(context_hint_set.get("hints"), list) else []
        campaign_key = clean_text(campaign_draft.get("campaign_key"))
        if not campaign_key or not intents:
            return {"ok": False, "error": "campaign_draft and intent_set required"}
        variants_per_intent = clamp_int(context.get("variants_per_intent"), 2, 2, 3)

        prompt = self._prompt(campaign_draft, product_brief, intent_set, context_hint_set, variants_per_intent)
        system = "You are a careful ad copywriter. Return valid JSON only."
        warnings = []

        data = None
        for attempt in range(2):
            data, err = ai_json(prompt, system, max_tokens=4000)
            if isinstance(data, dict) and isinstance(data.get("creatives"), list):
                rows = self._rows(data["creatives"], intents, variants_per_intent)
                invalid = [row for row in rows if len(row["headline"]) > 60 or len(row["body"]) > 200 or len(row["cta"]) > 25]
                if not invalid:
                    break
                prompt += "\nPrevious output exceeded length limits. Correct it strictly."
            if attempt == 1 and not isinstance(data, dict):
                data = {"creatives": self._fallback_creatives(product_brief, intents, variants_per_intent)}
                warnings.append("ai_creative_fallback")

        if not isinstance(data, dict) or not isinstance(data.get("creatives"), list):
            data = {"creatives": self._fallback_creatives(product_brief, intents, variants_per_intent)}
            warnings.append("ai_creative_fallback")

        creatives = self._rows(data["creatives"], intents, variants_per_intent)
        for row in creatives:
            if len(row["headline"]) > 60 or len(row["body"]) > 200 or len(row["cta"]) > 25:
                row["headline"] = clip(row["headline"], 60)
                row["body"] = clip(row["body"], 200)
                row["cta"] = clip(row["cta"], 25)
                if "creative_truncated_after_retry" not in warnings:
                    warnings.append("creative_truncated_after_retry")

        if len(creatives) < len(intents) * 2:
            creatives = self._rows(self._fallback_creatives(product_brief, intents, variants_per_intent), intents, variants_per_intent)
            if "ai_creative_fallback" not in warnings:
                warnings.append("ai_creative_fallback")
        creative_set = {"campaign_key": campaign_key, "creatives": creatives}

        if not context.get("dry_run", True):
            empresa_id = clean_text(campaign_draft.get("empresa_id") or product_brief.get("empresa_id") or context.get("empresa_id"))
            ctx = dict(context)
            schema = clean_text(ctx.get("schema") or ctx.get("supabase_schema") or ctx.get("db_schema"))
            if not schema:
                return {"ok": False, "error": "schema required for write"}
            ctx["company_id"] = empresa_id
            ctx["schema"] = schema
            try:
                rows = [{**row, "empresa_id": empresa_id, "campaign_key": campaign_key} for row in creatives]
                result = SupabaseClient(ctx).rest_upsert("creatives", rows, "empresa_id,campaign_key,creative_id")
                if not result.get("ok"):
                    return {"ok": False, "error": "db_persistence_failed"}
            except Exception:
                return {"ok": False, "error": "db_persistence_failed"}

        return {"ok": True, "data": {"creative_set": creative_set, "warnings": warnings}}

    def _prompt(self, campaign_draft: dict, product_brief: dict, intent_set: dict, context_hint_set: dict, variants: int) -> str:
        return (
            "Generate ad creatives for each intent. Do not invent commercial claims or product facts.\n"
            "Do not invent prices, discounts, certifications, guarantees, availability, or claims not present in ProductBrief.\n"
            f"Need {variants} variants per intent. Return pure JSON only.\n"
            "Length limits: headline <=60 chars, body <=200 chars, cta <=25 chars.\n"
            f"CampaignDraft:\n{json.dumps(campaign_draft, ensure_ascii=False)}\n"
            f"ProductBrief:\n{json.dumps(product_brief, ensure_ascii=False)}\n"
            f"IntentSet:\n{json.dumps(intent_set, ensure_ascii=False)}\n"
            f"ContextHintSet:\n{json.dumps(context_hint_set, ensure_ascii=False)}\n\n"
            'Return {"creatives":[{"intent_id":"int_001","headline":"...","body":"...","cta":"..."}]}'
        )

    def _rows(self, raw: list, intents: list, variants_per_intent: int) -> list[dict]:
        valid_intents = [clean_text(item.get("intent_id")) for item in intents if isinstance(item, dict)]
        counts = {intent_id: 0 for intent_id in valid_intents}
        rows = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            intent_id = clean_text(item.get("intent_id"))
            if intent_id not in counts or counts[intent_id] >= variants_per_intent:
                continue
            headline = clean_text(item.get("headline"))
            body = clean_text(item.get("body"))
            cta = clean_text(item.get("cta"))
            if not headline or not body or not cta:
                continue
            counts[intent_id] += 1
            rows.append(
                {
                    "creative_id": seq("cre", len(rows) + 1),
                    "intent_id": intent_id,
                    "headline": headline,
                    "body": body,
                    "cta": cta,
                    "variant": counts[intent_id],
                }
            )
        return rows

    def _fallback_creatives(self, product_brief: dict, intents: list, variants_per_intent: int) -> list[dict]:
        name = clean_text(product_brief.get("product_name")) or "tu solucion"
        value_props = product_brief.get("value_props") if isinstance(product_brief.get("value_props"), list) else []
        benefit = clean_text(value_props[0] if value_props else "mejorar tu operacion")
        rows = []
        for intent in intents:
            if not isinstance(intent, dict):
                continue
            intent_id = clean_text(intent.get("intent_id"))
            for variant in range(variants_per_intent):
                rows.append(
                    {
                        "intent_id": intent_id,
                        "headline": clip(f"{name} para equipos exigentes", 60),
                        "body": clip(f"Convierte interes en accion con una propuesta clara para {benefit}.", 200),
                        "cta": "Solicitar info" if variant == 0 else "Ver opciones",
                    }
                )
        return rows
