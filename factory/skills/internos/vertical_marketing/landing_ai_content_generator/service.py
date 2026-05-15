from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_property_service():
    service_path = Path(__file__).resolve().parents[1] / "property_landing_content_generator" / "service.py"
    spec = importlib.util.spec_from_file_location("factory_property_landing_content_service", service_path)
    if not spec or not spec.loader:
        raise ImportError(f"No se pudo cargar {service_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.PropertyLandingContentGeneratorService


class LandingAIContentGeneratorService:
    """Dispatch AI content generation by landing template type."""

    def ejecutar(self, context: dict) -> dict:
        template_type = str(context.get("template_type") or "property_sales").strip()
        if template_type == "property_sales":
            service_cls = _load_property_service()
            return service_cls().ejecutar(context)
        return {"ok": False, "error": f"template_type no soportado: {template_type}"}
