from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gptads_common import FUNNEL_STAGES, INTENT_TYPES, ai_json, clamp_int, clean_text, safe_priority, seq  # noqa: E402


class GptAdsIntentResearchService:
    def ejecutar(self, context: dict) -> dict:
        product_brief = context.get("product_brief") if isinstance(context.get("product_brief"), dict) else context
        product_key = clean_text(product_brief.get("product_key"))
        if not product_key:
            return {"ok": False, "error": "product_key required"}
        max_intents = clamp_int(context.get("max_intents"), 10, 5, 15)

        prompt = (
            "Generate conversational intents a ChatGPT user could express about this product. "
            "Do not return SEO keywords or Google Ads keyword lists. Return pure JSON only.\n"
            f"Need {max_intents} intents.\n"
            "Allowed intent_type: informacional, comparacion, compra. "
            "Allowed funnel_stage: awareness, consideration, decision. priority integer 1-5.\n"
            f"ProductBrief:\n{json.dumps(product_brief, ensure_ascii=False)}\n\n"
            'Return {"intents":[{"intent_text":"...","intent_type":"...","funnel_stage":"...","priority":1}]}'
        )
        system = "You are a conversational advertising researcher. Return valid JSON only."

        data = None
        for _ in range(2):
            data, err = ai_json(prompt, system, max_tokens=2200)
            if isinstance(data, dict) and isinstance(data.get("intents"), list):
                break
        if not isinstance(data, dict) or not isinstance(data.get("intents"), list):
            data = {"intents": self._fallback_intents(product_brief, max_intents)}

        intents = []
        for item in data["intents"]:
            if not isinstance(item, dict):
                continue
            text = clean_text(item.get("intent_text"))
            if not text:
                continue
            intent_type = clean_text(item.get("intent_type")).lower()
            funnel_stage = clean_text(item.get("funnel_stage")).lower()
            intents.append(
                {
                    "intent_id": seq("int", len(intents) + 1),
                    "intent_text": text,
                    "intent_type": intent_type if intent_type in INTENT_TYPES else "informacional",
                    "funnel_stage": funnel_stage if funnel_stage in FUNNEL_STAGES else "awareness",
                    "priority": safe_priority(item.get("priority")),
                }
            )
            if len(intents) >= max_intents:
                break

        if len(intents) < 5:
            intents = self._rows_from_fallback(product_brief, max_intents)
            warnings = ["ai_intent_fallback"]
        else:
            warnings = []
        return {"ok": True, "data": {"intent_set": {"product_key": product_key, "intents": intents}, "warnings": warnings}}

    def _fallback_intents(self, product_brief: dict, max_intents: int) -> list[dict]:
        name = clean_text(product_brief.get("product_name")) or "esta solucion"
        audience = clean_text((product_brief.get("market") or {}).get("audience")) or "mi empresa"
        base = [
            ("Como saber si " + name + " sirve para " + audience, "informacional", "awareness", 2),
            ("Que beneficios tiene " + name + " frente a alternativas", "comparacion", "consideration", 2),
            ("Cuanto cuesta implementar " + name, "compra", "decision", 1),
            ("Que incluye el servicio de " + name, "informacional", "consideration", 2),
            ("Como contratar " + name + " para mi equipo", "compra", "decision", 1),
            ("Que resultados puedo esperar con " + name, "informacional", "consideration", 3),
        ]
        return [
            {"intent_text": text, "intent_type": kind, "funnel_stage": stage, "priority": priority}
            for text, kind, stage, priority in base[:max_intents]
        ]

    def _rows_from_fallback(self, product_brief: dict, max_intents: int) -> list[dict]:
        rows = []
        for item in self._fallback_intents(product_brief, max_intents):
            rows.append(
                {
                    "intent_id": seq("int", len(rows) + 1),
                    "intent_text": item["intent_text"],
                    "intent_type": item["intent_type"],
                    "funnel_stage": item["funnel_stage"],
                    "priority": item["priority"],
                }
            )
        return rows
