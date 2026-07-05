from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gptads_common import TONES, ai_json, clean_text, ensure_market, nullable_text, seq, slug  # noqa: E402


class GptAdsProductBriefBuildService:
    def ejecutar(self, context: dict) -> dict:
        empresa_id = clean_text(context.get("empresa_id") or context.get("company_id"))
        product_name = clean_text(context.get("product_name"))
        if not empresa_id or not product_name:
            return {"ok": False, "error": "empresa_id and product_name are required"}

        product_key = clean_text(context.get("product_key")) or f"prod_{slug(product_name)[:40]}"
        base_market = ensure_market(context.get("market"))
        warnings = []
        if not context.get("product_key"):
            warnings.append("product_key_inferred")
        if not context.get("market"):
            warnings.append("market_defaulted")

        payload = {
            "empresa_id": empresa_id,
            "product_key": product_key,
            "product_name": product_name,
            "description": nullable_text(context.get("description")),
            "category": nullable_text(context.get("category")),
            "price_range": nullable_text(context.get("price_range")),
            "url": nullable_text(context.get("url")),
            "market": base_market,
        }

        prompt = (
            "Transform this ProductRef into a ProductBrief. Return pure JSON only.\n"
            "Rules: keep empresa_id, product_key, product_name, price_range and url exactly as provided; "
            "do not invent price_range or url. Complete description only if missing or too thin. "
            "Infer category only if missing. Normalize market.language as es-MX/en-US style. "
            "Generate exactly 3 value_props. tone must be profesional, casual, or urgente; default profesional. "
            "Use the real product category. If it is a consumer product, food, drink, craft, local product or retail item, "
            "do not use SaaS/B2B phrases like implement, operational friction, teams, platform, workflow, demo or quote.\n"
            f"ProductRef:\n{json.dumps(payload, ensure_ascii=False)}\n\n"
            "Return keys: description, category, market, value_props, tone, inferred_fields."
        )
        system = "You are a careful ad product strategist. Return valid JSON only."

        data = None
        for _ in range(2):
            data, err = ai_json(prompt, system)
            if isinstance(data, dict):
                break
        if not isinstance(data, dict):
            data = self._fallback(payload)
            warnings.append("ai_product_brief_fallback")

        description = nullable_text(data.get("description")) or payload["description"] or product_name
        category = nullable_text(data.get("category")) or payload["category"]
        market = ensure_market(data.get("market") if isinstance(data.get("market"), dict) else payload["market"])
        value_props = data.get("value_props") if isinstance(data.get("value_props"), list) else []
        value_props = [clean_text(item) for item in value_props if clean_text(item)][:3]
        while len(value_props) < 3:
            value_props.append(f"Beneficio claro {len(value_props) + 1} para {product_name}")
            warnings.append(f"value_prop_{len(value_props)}_fallback")
        tone = clean_text(data.get("tone")).lower()
        if tone not in TONES:
            tone = "profesional"
            warnings.append("tone_defaulted")

        inferred = data.get("inferred_fields") if isinstance(data.get("inferred_fields"), list) else []
        for item in inferred:
            key = clean_text(item)
            if key and key not in warnings:
                warnings.append(key)
        if not payload["description"] and "description_inferred" not in warnings:
            warnings.append("description_inferred")
        if not payload["category"] and "category_inferred" not in warnings:
            warnings.append("category_inferred")

        product_brief = {
            **payload,
            "description": description,
            "category": category,
            "market": market,
            "value_props": value_props,
            "tone": tone,
        }
        return {"ok": True, "data": {"product_brief": product_brief, "warnings": warnings}}

    def _fallback(self, payload: dict) -> dict:
        product_name = clean_text(payload.get("product_name"))
        description = nullable_text(payload.get("description")) or f"Producto enfocado en {product_name}."
        category = nullable_text(payload.get("category")) or self._category_from_text(product_name, description)
        kind = self._kind(product_name, description, category)
        if kind == "consumer_food":
            value_props = [
                self._origin_prop(product_name, description),
                self._quality_prop(product_name, description),
                self._story_prop(product_name, description),
            ]
        elif kind == "physical_product":
            value_props = [
                f"{product_name} con una propuesta clara y facil de entender",
                "Ideal para quienes buscan calidad, origen y confianza antes de comprar",
                "Presenta beneficios concretos sin promesas exageradas",
            ]
        else:
            value_props = [
                f"Comunica con claridad que problema resuelve {product_name}",
                "Ayuda al cliente a entender beneficios, alcance y siguiente paso",
                "Convierte interes inicial en una accion comercial concreta",
            ]
        return {
            "description": description,
            "category": category,
            "market": payload.get("market") or {},
            "value_props": value_props,
            "tone": "profesional",
            "inferred_fields": ["fallback_generated"],
        }

    def _kind(self, product_name: str, description: str, category: str) -> str:
        text = f"{product_name} {description} {category}".lower()
        food_words = ["cafe", "coffee", "organico", "chiapaneco", "miel", "cacao", "chocolate", "mezcal", "te ", "bebida", "alimento"]
        physical_words = ["500g", "kg", "bolsa", "paquete", "producto", "artesanal", "hecho", "elaborado", "tienda", "regalo"]
        if any(word in text for word in food_words):
            return "consumer_food"
        if any(word in text for word in physical_words):
            return "physical_product"
        return "service"

    def _category_from_text(self, product_name: str, description: str) -> str:
        text = f"{product_name} {description}".lower()
        if "cafe" in text or "coffee" in text:
            return "alimentos y bebidas"
        if "miel" in text or "cacao" in text or "chocolate" in text:
            return "alimentos artesanales"
        return "servicios"

    def _origin_prop(self, product_name: str, description: str) -> str:
        text = description.lower()
        if "jaltenango" in text and "chiapan" in text:
            return "Cafe organico de Jaltenango, Chiapas, con identidad regional"
        if "chiapan" in text:
            return "Origen chiapaneco que comunica autenticidad y tradicion"
        return f"Origen y elaboracion clara para valorar mejor {product_name}"

    def _quality_prop(self, product_name: str, description: str) -> str:
        if "organico" in description.lower():
            return "Perfil organico para consumidores que cuidan lo que compran"
        return f"Calidad cuidada para disfrutar {product_name} con confianza"

    def _story_prop(self, product_name: str, description: str) -> str:
        text = description.lower()
        if "mujeres" in text:
            return "Elaborado por mujeres de la region, con una historia que conecta"
        if "region" in text or "artesanal" in text:
            return "Historia local que hace la compra mas significativa"
        return "Narrativa humana que diferencia el producto de opciones genericas"
