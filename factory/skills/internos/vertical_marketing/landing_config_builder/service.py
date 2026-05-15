from __future__ import annotations

import json
from pathlib import Path


class LandingConfigBuilderService:
    """Build normalized config for landing templates."""

    def ejecutar(self, context: dict) -> dict:
        template_type = str(context.get("template_type") or "property_sales").strip()
        if template_type != "property_sales":
            return {"ok": False, "error": f"template_type no soportado: {template_type}"}

        config = self._property_sales(context)
        output_path = context.get("output_path")
        dry_run = bool(context.get("dry_run", True))
        if output_path and not dry_run:
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(config, ensure_ascii=True, indent=2), encoding="utf-8")

        return {"ok": True, "data": {"template_type": template_type, "config": config, "output_path": output_path, "dry_run": dry_run}}

    def _property_sales(self, context: dict) -> dict:
        campaign = context.get("campaign") or {}
        data = context.get("data") or {}
        prop = context.get("property") or data.get("property") or (campaign.get("brief") or {}).get("property") or data
        company_id = context.get("company_id") or campaign.get("company_id") or "EMPRESA"
        building = prop.get("building") or prop.get("property_name") or "Propiedad"
        location = prop.get("location") or "Ubicacion por confirmar"
        floor = prop.get("floor")
        size = prop.get("size_m2")
        capacity = prop.get("capacity") or "Por confirmar"
        price = prop.get("price_range") or data.get("price_label") or "Precio por confirmar"
        rent = prop.get("current_rent")
        rent_label = f"MXN {rent:,.0f}" if isinstance(rent, (int, float)) else (str(rent) if rent else "Por confirmar")
        occupancy = prop.get("occupancy_options") or "Por confirmar"
        main_image = data.get("main_image_url") or campaign.get("image_url") or ""
        gallery = data.get("gallery_urls") or []
        config = {
            "company_id": company_id,
            "campaign_slug": context.get("campaign_slug") or campaign.get("campaign_slug") or "first_campaign",
            "template_type": "property_sales",
            "page_title": data.get("page_title") or f"{building} | {location}",
            "meta_description": data.get("meta_description") or f"Propiedad en {location}. Solicita ficha y agenda una visita.",
            "brand": data.get("brand") or company_id,
            "eyebrow": data.get("eyebrow") or f"{building} - {location}" + (f" - Piso {floor}" if floor else ""),
            "headline_accent": data.get("headline_accent") or "Propiedad lista para evaluar",
            "headline_main": data.get("headline_main") or f"en {building}",
            "subtitle": data.get("subtitle") or "Conoce datos clave, fotos y condiciones comerciales de esta propiedad.",
            "price_label": data.get("price_label") or str(price),
            "price_note": data.get("price_note") or str(prop.get("operation_type") or "Operacion por confirmar"),
            "cta_label": data.get("cta_label") or "Solicitar informacion por WhatsApp",
            "secondary_cta_label": data.get("secondary_cta_label") or "Ver ficha",
            "whatsapp_number": data.get("whatsapp_number") or campaign.get("whatsapp_number") or "",
            "whatsapp_message": data.get("whatsapp_message") or f"Hola, quiero informacion de {prop.get('property_name') or building}.",
            "section_title": data.get("section_title") or "Ficha de la propiedad",
            "section_copy": data.get("section_copy") or "Informacion general de la propiedad para evaluar si encaja con tu objetivo.",
            "facts": data.get("facts") or [
                {"label": "Superficie", "value": f"{size} m2" if size else "Por confirmar"},
                {"label": "Nivel", "value": f"Piso {floor}" if floor else "Por confirmar"},
                {"label": "Capacidad", "value": str(capacity)},
                {"label": "Renta actual", "value": rent_label},
                {"label": "Entrega", "value": str(occupancy)},
            ],
            "benefits": data.get("benefits") or [
                {"title": "Informacion clara", "text": "Datos principales disponibles para una primera evaluacion."},
                {"title": "Contacto directo", "text": "Solicita ficha o agenda una visita por WhatsApp."},
                {"title": "Condiciones revisables", "text": "Confirma disponibilidad, documentacion y terminos con el asesor."},
                {"title": "Uso flexible", "text": "Evalua la propiedad para uso propio o estrategia patrimonial."},
            ],
            "investment_title": data.get("investment_title") or "Datos para evaluar inversion",
            "investment_copy": data.get("investment_copy") or "La informacion financiera se presenta como dato actual reportado. No representa garantia de rendimiento futuro.",
            "investment_facts": data.get("investment_facts") or [
                {"label": "Precio", "value": str(price)},
                {"label": "Renta actual", "value": rent_label},
                {"label": "Operacion", "value": str(prop.get("operation_type") or "Por confirmar")},
                {"label": "Disponibilidad", "value": str(occupancy)},
            ],
            "contact_title": data.get("contact_title") or "Solicita ficha o agenda visita",
            "contact_copy": data.get("contact_copy") or "Envia un mensaje para recibir mas informacion y coordinar el siguiente paso.",
            "footer_text": data.get("footer_text") or f"{company_id} - {building}",
            "privacy_url": data.get("privacy_url") or campaign.get("privacy_url") or "privacy.html",
            "main_image_url": main_image,
            "gallery_urls": gallery,
        }
        return config
