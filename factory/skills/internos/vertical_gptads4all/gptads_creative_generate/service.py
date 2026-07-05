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
                rows = [
                    {
                        **row,
                        "empresa_id": empresa_id,
                        "company_id": empresa_id,
                        "product_id": clean_text(context.get("product_id") or campaign_draft.get("product_id")) or None,
                        "brief_id": clean_text(context.get("brief_id") or campaign_draft.get("brief_id")) or None,
                        "campaign_key": campaign_key,
                    }
                    for row in creatives
                ]
                result = SupabaseClient(ctx).rest_upsert("creatives", rows, "empresa_id,campaign_key,creative_id")
                if not result.get("ok") and any(col in str(result.get("error") or "") for col in ["company_id", "product_id", "brief_id"]):
                    legacy_rows = []
                    for row in rows:
                        legacy = dict(row)
                        for key in ("company_id", "product_id", "brief_id"):
                            legacy.pop(key, None)
                        legacy_rows.append(legacy)
                    result = SupabaseClient(ctx).rest_upsert("creatives", legacy_rows, "empresa_id,campaign_key,creative_id")
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
            "Match the real product. If it is coffee, food, craft or retail, write consumer ads about origin, taste, story, gift/use and purchase. "
            "Do not use SaaS/B2B words like teams, implement, operational, workflow, demo, quote or platform.\n"
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
        description = clean_text(product_brief.get("description"))
        category = clean_text(product_brief.get("category"))
        value_props = product_brief.get("value_props") if isinstance(product_brief.get("value_props"), list) else []
        text = f"{name} {description} {category}".lower()
        if self._is_consumer_food(text):
            templates = self._consumer_food_templates(name, description, value_props)
        elif self._is_physical_product(text):
            templates = self._physical_product_templates(name, value_props)
        else:
            templates = self._service_templates(name, value_props)
        rows = []
        for intent in intents:
            if not isinstance(intent, dict):
                continue
            intent_id = clean_text(intent.get("intent_id"))
            for variant in range(variants_per_intent):
                template = templates[variant % len(templates)]
                rows.append(
                    {
                        "intent_id": intent_id,
                        "headline": clip(template["headline"], 60),
                        "body": clip(template["body"], 200),
                        "cta": clip(template["cta"], 25),
                    }
                )
        return rows

    def _is_consumer_food(self, text: str) -> bool:
        return any(word in text for word in ["cafe", "coffee", "organico", "chiapaneco", "miel", "cacao", "chocolate", "mezcal", "bebida", "alimento"])

    def _is_physical_product(self, text: str) -> bool:
        return any(word in text for word in ["500g", "kg", "bolsa", "paquete", "producto", "artesanal", "hecho", "elaborado", "tienda", "regalo"])

    def _consumer_food_templates(self, name: str, description: str, value_props: list) -> list[dict]:
        desc = description.lower()
        origin = "de Jaltenango, Chiapas" if "jaltenango" in desc else "de origen chiapaneco" if "chiapan" in desc else "con origen cuidado"
        story = "elaborado por mujeres de la region" if "mujeres" in desc else "con una historia local que se nota"
        prop = clean_text(value_props[0] if value_props else f"{name} con identidad y sabor")
        return [
            {
                "headline": f"Cafe organico {origin}",
                "body": f"Disfruta {name}: {story}, con una propuesta honesta para quienes buscan sabor, origen y consumo consciente.",
                "cta": "Comprar cafe",
            },
            {
                "headline": "Sabor chiapaneco en tu taza",
                "body": f"{prop}. Una opcion para regalar, compartir o convertir tu cafe diario en una compra con sentido.",
                "cta": "Ver presentacion",
            },
            {
                "headline": "Cafe con origen e historia",
                "body": f"{name} comunica calidad, region y trabajo local sin sonar generico. Ideal para consumidores que valoran lo autentico.",
                "cta": "Conocer mas",
            },
        ]

    def _physical_product_templates(self, name: str, value_props: list) -> list[dict]:
        prop = clean_text(value_props[0] if value_props else f"{name} con una propuesta clara")
        return [
            {"headline": f"{name} con calidad real", "body": f"{prop}. Presenta beneficios claros para decidir sin rodeos.", "cta": "Ver producto"},
            {"headline": f"Elige {name}", "body": "Una opcion pensada para quien compara calidad, origen y confianza antes de comprar.", "cta": "Comprar ahora"},
            {"headline": f"{name} sin vueltas", "body": "Comunica lo importante: que es, por que conviene y cual es el siguiente paso.", "cta": "Conocer mas"},
        ]

    def _service_templates(self, name: str, value_props: list) -> list[dict]:
        benefit = clean_text(value_props[0] if value_props else "resolver una necesidad concreta")
        return [
            {"headline": f"{name} para crecer", "body": f"Convierte interes en accion con una propuesta clara para {benefit}.", "cta": "Solicitar info"},
            {"headline": f"Conoce {name}", "body": "Explica beneficios, alcance y siguiente paso sin promesas exageradas.", "cta": "Ver opciones"},
            {"headline": f"Empieza con {name}", "body": "Una forma simple de presentar valor y mover al cliente hacia la accion.", "cta": "Empezar"},
        ]
