from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gptads_common import OBJECTIVES, ai_json, clean_text, ensure_market, nullable_text  # noqa: E402
from gptads_library import product_key_from_name  # noqa: E402


class GptAdsBriefAnalyzeService:
    def ejecutar(self, context: dict) -> dict:
        empresa_id = clean_text(context.get("empresa_id") or context.get("company_id"))
        raw_brief = clean_text(context.get("raw_brief") or context.get("description"))
        if not empresa_id:
            return {"ok": False, "error": "empresa_id or company_id is required"}
        if len(raw_brief) < 30:
            return {"ok": False, "error": "raw_brief debe tener al menos 30 caracteres"}

        market = ensure_market(context.get("market"))
        output_language = self._output_language(context.get("output_language") or context.get("brief_language") or market.get("language"))
        payload = {
            "empresa_id": empresa_id,
            "raw_brief": raw_brief,
            "product_name": nullable_text(context.get("product_name")),
            "product_key": nullable_text(context.get("product_key")),
            "category": nullable_text(context.get("category")),
            "daily_budget_amount": context.get("daily_budget_amount"),
            "currency": nullable_text(context.get("currency")),
            "market": market,
            "output_language": output_language,
            "available_objectives": sorted(OBJECTIVES),
            "goal": (
                "Prepare the advertiser to be understood and selected in conversational discovery, "
                "answer engines and search/chat buying journeys in the United States or the selected market."
            ),
        }
        prompt = (
            "Analyze this advertiser brief before campaign generation. Return pure JSON only.\n"
            "Do not generate ads yet. Extract only what is supported by the brief. "
            "If information is missing, list it in missing_fields. "
            "Recommend exactly one objective from conversions, leads, traffic. "
            "Create an optimized_description that can feed an ad generation pipeline. "
            f"Write every user-facing field in {output_language}. If the brief is in another language, translate and localize it. "
            f"Do not mix languages. The only fields that may stay in English are enum/code fields: objective_recommended and market.language. "
            "Keep objective_recommended as one of the exact enum values: conversions, leads, traffic. "
            "For physical products, avoid SaaS language like implement, workflow, platform, demo, friction or teams. "
            "For USA readiness, include wording that helps conversational assistants understand origin, audience, "
            "differentiators, proof, objections and next action.\n"
            f"Brief:\n{json.dumps(payload, ensure_ascii=False)}\n\n"
            "Return keys: product_name, category, audience, market, objective_recommended, objective_reason, "
            "channel_recommended, cta_recommended, differentiators, objections, creative_angles, missing_fields, "
            "quality_score, optimized_description, prompt_optimized."
        )
        system = (
            "You are a senior performance marketing strategist for conversational commerce. "
            f"Return valid JSON only. All human-readable copy must be written in {output_language}."
        )

        data = None
        warnings = []
        for _ in range(2):
            data, err = ai_json(prompt, system, max_tokens=2200)
            if isinstance(data, dict):
                break
        if not isinstance(data, dict):
            data = self._fallback(payload)
            warnings.append("ai_brief_analysis_fallback")

        analysis = self._normalize(data, payload)
        return {"ok": True, "data": {"brief_analysis": analysis, "warnings": warnings}}

    def _normalize(self, data: dict, payload: dict) -> dict:
        raw = payload["raw_brief"]
        output_language = payload.get("output_language") or "es"
        product_name = clean_text(data.get("product_name") or payload.get("product_name") or self._infer_product(raw))
        category = clean_text(data.get("category") or payload.get("category") or self._infer_category(raw))
        objective = clean_text(data.get("objective_recommended")).lower()
        if objective not in OBJECTIVES:
            objective = self._objective_from_text(raw)
        market = ensure_market(data.get("market") if isinstance(data.get("market"), dict) else payload.get("market"))
        missing = self._filter_missing(self._clean_list(data.get("missing_fields")), payload)
        for field in self._required_missing(payload):
            if field not in missing:
                missing.append(field)
        optimized = clean_text(data.get("optimized_description")) or self._optimized_description(product_name, raw)
        prompt_optimized = clean_text(data.get("prompt_optimized")) or self._prompt(product_name, optimized, objective)
        return {
            "product_name": product_name,
            "product_key": clean_text(payload.get("product_key")) or product_key_from_name(product_name),
            "category": category,
            "audience": clean_text(data.get("audience") or self._audience_from_text(raw)),
            "market": market,
            "output_language": output_language,
            "objective_recommended": objective,
            "objective_reason": clean_text(data.get("objective_reason") or self._objective_reason(objective)),
            "channel_recommended": clean_text(data.get("channel_recommended") or self._channel_from_text(raw)),
            "cta_recommended": clean_text(data.get("cta_recommended") or self._cta_from_objective(objective)),
            "differentiators": self._clean_list(data.get("differentiators"))[:5] or self._differentiators(raw),
            "objections": self._clean_list(data.get("objections"))[:5] or ["precio", "confianza", "calidad real"],
            "creative_angles": self._clean_list(data.get("creative_angles"))[:6] or self._angles(raw),
            "missing_fields": missing[:8],
            "quality_score": self._quality_score(raw, missing, payload),
            "optimized_description": optimized,
            "prompt_optimized": prompt_optimized,
        }

    def _fallback(self, payload: dict) -> dict:
        raw = payload["raw_brief"]
        product_name = payload.get("product_name") or self._infer_product(raw)
        objective = self._objective_from_text(raw)
        optimized = self._optimized_description(product_name, raw)
        return {
            "product_name": product_name,
            "product_key": clean_text(payload.get("product_key")) or product_key_from_name(product_name),
            "category": payload.get("category") or self._infer_category(raw),
            "audience": self._audience_from_text(raw),
            "market": payload.get("market") or {},
            "output_language": payload.get("output_language") or "es",
            "objective_recommended": objective,
            "objective_reason": self._objective_reason(objective),
            "channel_recommended": self._channel_from_text(raw),
            "cta_recommended": self._cta_from_objective(objective),
            "differentiators": self._differentiators(raw),
            "objections": ["precio", "confianza", "calidad real"],
            "creative_angles": self._angles(raw),
            "missing_fields": self._required_missing(payload),
            "quality_score": self._quality_score(raw, self._required_missing(payload), payload),
            "optimized_description": optimized,
            "prompt_optimized": self._prompt(product_name, optimized, objective),
        }

    def _clean_list(self, value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        return [clean_text(item) for item in value if clean_text(item)]

    def _output_language(self, value: object) -> str:
        text = clean_text(value).lower()
        if text in {"en", "english", "en-us", "ingles", "inglés"}:
            return "English"
        return "Spanish"

    def _infer_product(self, text: str) -> str:
        first = clean_text(text.split(".")[0])
        return first[:90] or "Producto o servicio"

    def _infer_category(self, text: str) -> str:
        lower = text.lower()
        if "cafe" in lower or "coffee" in lower:
            return "alimentos y bebidas"
        if "software" in lower or "app" in lower or "saas" in lower:
            return "software"
        if "servicio" in lower:
            return "servicios"
        return "producto comercial"

    def _objective_from_text(self, text: str) -> str:
        lower = text.lower()
        if "lead" in lower or "whatsapp" in lower or "contact" in lower:
            return "leads"
        if "trafico" in lower or "traffic" in lower or "visitas" in lower:
            return "traffic"
        return "conversions"

    def _objective_reason(self, objective: str) -> str:
        reasons = {
            "leads": "Conviene captar interesados y abrir conversacion antes de cerrar la venta.",
            "traffic": "Conviene llevar usuarios a una pagina o tienda para educar y medir interes.",
            "conversions": "Conviene empujar compra o accion directa cuando la oferta ya esta clara.",
        }
        return reasons.get(objective, reasons["conversions"])

    def _channel_from_text(self, text: str) -> str:
        lower = text.lower()
        if "whatsapp" in lower:
            return "WhatsApp"
        if "amazon" in lower or "marketplace" in lower:
            return "Marketplace"
        if "web" in lower or "pagina" in lower or "site" in lower:
            return "Pagina web"
        return "WhatsApp o landing page"

    def _cta_from_objective(self, objective: str) -> str:
        if objective == "leads":
            return "Solicitar informacion"
        if objective == "traffic":
            return "Ver mas"
        return "Comprar ahora"

    def _filter_missing(self, missing: list[str], payload: dict) -> list[str]:
        text = f"{payload.get('raw_brief') or ''} {payload.get('currency') or ''} {payload.get('market') or ''}".lower()
        budget = payload.get("daily_budget_amount")
        filtered = []
        for item in missing:
            lower = item.lower()
            if ("budget" in lower or "spend" in lower or "presupuesto" in lower) and budget:
                continue
            if ("price" in lower or "precio" in lower or "pricing" in lower) and any(token in text for token in ["$", "precio", "price", "mxn", "usd"]):
                continue
            if ("geo" in lower or "zona" in lower or "geographic" in lower or "market" in lower) and (payload.get("market") or {}).get("country"):
                continue
            if ("audience" in lower or "audiencia" in lower) and (payload.get("market") or {}).get("audience"):
                continue
            filtered.append(item)
        return filtered

    def _required_missing(self, payload: dict) -> list[str]:
        text = f"{payload.get('raw_brief') or ''} {payload.get('currency') or ''}".lower()
        market = payload.get("market") if isinstance(payload.get("market"), dict) else {}
        lower = text.lower()
        checks = [
            ("precio o rango", ["$", "precio", "costo", "usd", "mxn"]),
            ("canal de contacto", ["whatsapp", "web", "landing", "formulario", "telefono", "tienda"]),
            ("objeciones frecuentes", ["objecion", "dudan", "preguntan", "comparan", "confianza"]),
        ]
        missing = [label for label, words in checks if not any(word in lower for word in words)]
        if not market.get("country") and not any(word in lower for word in ["usa", "estados unidos", "mexico", "ciudad", "zona", "envio"]):
            missing.append("zona de venta")
        if not payload.get("daily_budget_amount"):
            missing.append("presupuesto diario")
        return missing

    def _quality_score(self, text: str, missing: list[str], payload: dict) -> int:
        lower = text.lower()
        proof_terms = ["puntaje", "score", "certific", "organico", "cooperativa", "precio", "altura", "msnm", "variedad", "arabica"]
        proof_bonus = min(12, sum(2 for term in proof_terms if term in lower))
        market_bonus = 5 if (payload.get("market") or {}).get("country") else 0
        budget_bonus = 5 if payload.get("daily_budget_amount") else 0
        score = 55 + min(25, len(text) // 35) + proof_bonus + market_bonus + budget_bonus - (len(missing) * 4)
        return max(35, min(95, score))

    def _audience_from_text(self, text: str) -> str:
        lower = text.lower()
        if "gourmet" in lower or "especialidad" in lower:
            return "Compradores de productos premium, gourmet o de especialidad"
        if "empresa" in lower or "corporativo" in lower:
            return "Compradores empresariales y decisores comerciales"
        return "Clientes interesados en una compra con calidad, confianza y diferenciacion"

    def _differentiators(self, text: str) -> list[str]:
        lower = text.lower()
        items = []
        if "organico" in lower:
            items.append("producto organico")
        if "mujeres" in lower:
            items.append("elaborado por mujeres productoras")
        if "chiapas" in lower or "jaltenango" in lower:
            items.append("origen regional claro")
        if "artesanal" in lower:
            items.append("proceso artesanal")
        return items or ["propuesta diferenciada", "beneficio claro", "historia de marca"]

    def _angles(self, text: str) -> list[str]:
        base = ["origen e historia", "calidad y confianza", "prueba social", "regalo o ocasion", "facilidad de compra"]
        if "whatsapp" in text.lower():
            base.append("pedido rapido por WhatsApp")
        return base

    def _optimized_description(self, product_name: str, raw: str) -> str:
        return (
            f"{product_name}. Brief comercial: {raw} "
            "La campana debe explicar claramente que se vende, para quien es, por que conviene, "
            "que objeciones puede tener el comprador y cual es el siguiente paso de contacto o compra."
        )

    def _prompt(self, product_name: str, optimized: str, objective: str) -> str:
        return (
            f"Genera una campana para {product_name} con objetivo {objective}. "
            f"Usa este brief optimizado: {optimized} "
            "Prioriza claridad, intencion de compra, diferenciadores verificables, CTA concreto y lenguaje natural para busqueda conversacional."
        )
