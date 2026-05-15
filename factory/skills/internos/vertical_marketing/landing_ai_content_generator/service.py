from __future__ import annotations

from pathlib import Path


def _runner():
    from factory.engine import SkillLoader, SkillRunner

    root = Path(__file__).resolve().parents[2]
    ext_root = root.parent / "externos"
    ext_root.mkdir(parents=True, exist_ok=True)
    loader = SkillLoader(
        internal_root=root,
        external_root=ext_root,
        extra_roots={"meta": root.parent / "meta", "eval": root.parent / "eval"},
    )
    return SkillRunner(loader)


class LandingAIContentGeneratorService:
    """Dispatch AI content generation by landing template type."""

    def ejecutar(self, context: dict) -> dict:
        template_type = str(context.get("template_type") or "property_sales").strip()
        if template_type == "property_sales":
            return _runner().run(
                "vertical_marketing/property_landing_content_generator",
                context,
                source="internos",
            )
        return {"ok": False, "error": f"template_type no soportado: {template_type}"}
