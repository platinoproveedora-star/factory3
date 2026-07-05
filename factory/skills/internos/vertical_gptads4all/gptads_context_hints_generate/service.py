from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gptads_common import ai_json, clamp_int, clean_text, safe_priority, seq  # noqa: E402


class GptAdsContextHintsGenerateService:
    def ejecutar(self, context: dict) -> dict:
        product_brief = context.get("product_brief") if isinstance(context.get("product_brief"), dict) else {}
        intent_set = context.get("intent_set") if isinstance(context.get("intent_set"), dict) else {}
        intents = intent_set.get("intents") if isinstance(intent_set.get("intents"), list) else []
        product_key = clean_text(intent_set.get("product_key") or product_brief.get("product_key"))
        valid_intents = {clean_text(item.get("intent_id")) for item in intents if isinstance(item, dict)}
        if not product_key or not valid_intents:
            return {"ok": False, "error": "product_brief and intent_set required"}
        hints_per_intent = clamp_int(context.get("hints_per_intent"), 2, 1, 3)

        prompt = (
            "Generate conversational context hints for each intent. These are not search keywords. "
            "hint_text must describe a conversational signal/context. Return pure JSON only.\n"
            f"Need {hints_per_intent} hints per intent.\n"
            "Each item must reference an existing intent_id. trigger_keywords max 5 strings.\n"
            f"ProductBrief:\n{json.dumps(product_brief, ensure_ascii=False)}\n"
            f"IntentSet:\n{json.dumps(intent_set, ensure_ascii=False)}\n\n"
            'Return {"hints":[{"intent_id":"int_001","hint_text":"...","trigger_keywords":["..."],"priority":1}]}'
        )
        system = "You create conversational context signals for ads. Return valid JSON only."

        for attempt in range(2):
            data, err = ai_json(prompt, system, max_tokens=2600)
            if not isinstance(data, dict) or not isinstance(data.get("hints"), list):
                if attempt == 1:
                    data = {"hints": self._fallback_hints(intents, hints_per_intent)}
                    break
                continue
            if self._references_ok(data["hints"], valid_intents):
                break
            if attempt == 1:
                data = {"hints": self._fallback_hints(intents, hints_per_intent)}
                break
        else:
            return {"ok": False, "error": "ai_response_not_parseable"}

        hints = []
        for item in data["hints"]:
            if not isinstance(item, dict):
                continue
            intent_id = clean_text(item.get("intent_id"))
            hint_text = clean_text(item.get("hint_text"))
            if intent_id not in valid_intents or not hint_text:
                continue
            raw_keywords = item.get("trigger_keywords") if isinstance(item.get("trigger_keywords"), list) else []
            keywords = []
            for kw in raw_keywords:
                text = clean_text(kw).lower()
                if text and text not in keywords:
                    keywords.append(text)
                if len(keywords) >= 5:
                    break
            hints.append(
                {
                    "hint_id": seq("hint", len(hints) + 1),
                    "intent_id": intent_id,
                    "hint_text": hint_text,
                    "trigger_keywords": keywords,
                    "priority": safe_priority(item.get("priority")),
                }
            )

        intent_ids_with_hints = {hint["intent_id"] for hint in hints}
        if not valid_intents.issubset(intent_ids_with_hints):
            hints = self._rows_from_fallback(intents, hints_per_intent)
            warnings = ["ai_context_hint_fallback"]
        else:
            warnings = []
        return {"ok": True, "data": {"context_hint_set": {"product_key": product_key, "hints": hints}, "warnings": warnings}}

    def _references_ok(self, hints: list, valid_intents: set[str]) -> bool:
        for item in hints:
            if isinstance(item, dict) and clean_text(item.get("intent_id")) not in valid_intents:
                return False
        return True

    def _fallback_hints(self, intents: list, hints_per_intent: int) -> list[dict]:
        rows = []
        for intent in intents:
            if not isinstance(intent, dict):
                continue
            intent_id = clean_text(intent.get("intent_id"))
            intent_text = clean_text(intent.get("intent_text"))
            for _ in range(hints_per_intent):
                rows.append(
                    {
                        "intent_id": intent_id,
                        "hint_text": f"Usuario pregunta: {intent_text}",
                        "trigger_keywords": [kw for kw in intent_text.lower().split()[:5] if kw],
                        "priority": intent.get("priority") or 2,
                    }
                )
        return rows

    def _rows_from_fallback(self, intents: list, hints_per_intent: int) -> list[dict]:
        rows = []
        for item in self._fallback_hints(intents, hints_per_intent):
            rows.append(
                {
                    "hint_id": seq("hint", len(rows) + 1),
                    "intent_id": clean_text(item.get("intent_id")),
                    "hint_text": clean_text(item.get("hint_text")),
                    "trigger_keywords": item.get("trigger_keywords") or [],
                    "priority": safe_priority(item.get("priority")),
                }
            )
        return rows
