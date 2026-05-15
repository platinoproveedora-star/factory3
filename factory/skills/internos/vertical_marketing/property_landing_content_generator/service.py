from __future__ import annotations

import json
import os
import re
import urllib.request


class PropertyLandingContentGeneratorService:
    """Generate structured real estate landing content."""

    def ejecutar(self, context: dict) -> dict:
        prop = context.get("property") or context.get("propiedad") or {}
        campaign = context.get("campaign") or {}
        company_id = str(context.get("company_id") or context.get("empresa_id") or campaign.get("company_id") or "").strip()
        if not prop:
            return {"ok": False, "error": "property requerido"}

        fallback = self._fallback(company_id, prop, campaign)
        if context.get("dry_run", True):
            return {"ok": True, "data": {**fallback, "dry_run": True}}

        prompt = (
            "Genera contenido para una landing inmobiliaria dinamica.\n"
            "Debe sonar profesional, claro, sobrio y orientado a conversion.\n"
            "No prometas rendimientos garantizados. Si mencionas renta o inversion, dilo como dato actual reportado.\n\n"
            f"EMPRESA: {company_id or 'n/a'}\n"
            f"PROPIEDAD JSON:\n{json.dumps(prop, ensure_ascii=False, indent=2)}\n\n"
            f"CAMPANA JSON:\n{json.dumps(campaign, ensure_ascii=False, indent=2)}\n\n"
            "Devuelve JSON valido EXACTAMENTE con estas llaves:\n"
            "{"
            '"page_title":"...",'
            '"meta_description":"...",'
            '"brand":"...",'
            '"eyebrow":"...",'
            '"headline_accent":"...",'
            '"headline_main":"...",'
            '"subtitle":"...",'
            '"price_label":"...",'
            '"price_note":"...",'
            '"cta_label":"...",'
            '"secondary_cta_label":"...",'
            '"whatsapp_message":"...",'
            '"section_title":"...",'
            '"section_copy":"...",'
            '"facts":[{"label":"...","value":"..."}],'
            '"benefits":[{"title":"...","text":"..."}],'
            '"investment_title":"...",'
            '"investment_copy":"...",'
            '"investment_facts":[{"label":"...","value":"..."}],'
            '"contact_title":"...",'
            '"contact_copy":"...",'
            '"footer_text":"..."'
            "}"
        )
        result = self._haiku(prompt)
        if not result.get("ok"):
            return result
        data = result.get("data") or {}
        return {"ok": True, "data": {**fallback, **data}}

    def _fallback(self, company_id: str, prop: dict, campaign: dict) -> dict:
        building = prop.get("building") or prop.get("property_name") or "Propiedad"
        location = prop.get("location") or "Ubicacion por confirmar"
        floor = prop.get("floor")
        price = prop.get("price_range") or campaign.get("price_range") or "Precio por confirmar"
        rent = prop.get("current_rent")
        rent_value = f"MXN {rent:,.0f}".replace(",", ",") if isinstance(rent, (int, float)) else (str(rent) if rent else "Por confirmar")
        size = prop.get("size_m2")
        capacity = prop.get("capacity") or "Por confirmar"
        occupancy = prop.get("occupancy_options") or "Por confirmar"
        return {
            "page_title": f"{building} | {location}",
            "meta_description": f"Propiedad en {location}. Informacion, fotos y contacto para solicitar ficha.",
            "brand": company_id or "Campana inmobiliaria",
            "eyebrow": f"{building} · {location}" + (f" · Piso {floor}" if floor else ""),
            "headline_accent": "Propiedad lista para evaluar",
            "headline_main": f"en {building}",
            "subtitle": "Conoce los datos clave, beneficios y condiciones comerciales de esta propiedad.",
            "price_label": str(price),
            "price_note": str(prop.get("operation_type") or "Operacion por confirmar"),
            "cta_label": "Solicitar informacion por WhatsApp",
            "secondary_cta_label": "Ver ficha",
            "whatsapp_message": f"Hola, quiero informacion de {prop.get('property_name') or building}.",
            "section_title": "Ficha de la propiedad",
            "section_copy": "Informacion general de la propiedad para revisar si encaja con tu objetivo de compra o inversion.",
            "facts": [
                {"label": "Superficie", "value": f"{size} m2" if size else "Por confirmar"},
                {"label": "Nivel", "value": f"Piso {floor}" if floor else "Por confirmar"},
                {"label": "Capacidad", "value": str(capacity)},
                {"label": "Renta actual", "value": rent_value},
                {"label": "Entrega", "value": str(occupancy)},
            ],
            "benefits": [
                {"title": "Informacion clara", "text": "Datos principales disponibles para una primera evaluacion."},
                {"title": "Contacto directo", "text": "Solicita ficha o agenda una visita por WhatsApp."},
                {"title": "Condiciones revisables", "text": "Confirma disponibilidad, documentacion y terminos con el asesor."},
                {"title": "Uso flexible", "text": "Evalua la propiedad para uso propio o estrategia patrimonial."},
            ],
            "investment_title": "Datos para evaluar inversion",
            "investment_copy": "La informacion financiera se presenta como dato actual reportado. No representa garantia de rendimiento futuro.",
            "investment_facts": [
                {"label": "Precio", "value": str(price)},
                {"label": "Renta actual", "value": rent_value},
                {"label": "Operacion", "value": str(prop.get("operation_type") or "Por confirmar")},
                {"label": "Disponibilidad", "value": str(occupancy)},
            ],
            "contact_title": "Solicita ficha o agenda visita",
            "contact_copy": "Envia un mensaje para recibir mas informacion, resolver dudas y coordinar el siguiente paso.",
            "footer_text": f"{company_id or 'Campana'} · {building}",
        }

    def _haiku(self, prompt: str) -> dict:
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            return {"ok": False, "error": "ANTHROPIC_API_KEY no configurada"}
        try:
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=json.dumps({
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 2200,
                    "system": "Eres un estratega senior de marketing inmobiliario. Responde SIEMPRE en JSON valido, sin markdown.",
                    "messages": [{"role": "user", "content": prompt}],
                }).encode(),
                headers={
                    "content-type": "application/json",
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=45) as response:
                raw = json.loads(response.read().decode())["content"][0]["text"].strip()
            parsed = self._parse_json(raw)
            if parsed is None:
                return {"ok": False, "error": "respuesta IA no fue JSON valido", "raw_preview": raw[:1000]}
            return {"ok": True, "data": parsed}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _parse_json(self, raw: str) -> dict | None:
        text = raw.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
            text = re.sub(r"\s*```$", "", text).strip()
        try:
            data = json.loads(text)
            return data if isinstance(data, dict) else None
        except Exception:
            pass
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        try:
            data = json.loads(text[start : end + 1])
            return data if isinstance(data, dict) else None
        except Exception:
            return None
