from __future__ import annotations

from pathlib import Path


class LandingTemplateRendererService:
    """Render HTML landing from a versioned template."""

    def ejecutar(self, context: dict) -> dict:
        template_type = str(context.get("template_type") or "property_sales").strip()
        root = Path(__file__).resolve().parents[5]
        template_dir = root / "factory" / "templates" / "landing" / template_type
        template_path = template_dir / "index.html"
        if not template_path.exists():
            return {"ok": False, "error": f"template no encontrado: {template_type}"}
        landing_config_url = str(context.get("landing_config_url") or "__LANDING_CONFIG_URL__").strip()
        output_dir = Path(context.get("output_dir") or "dist/landing")
        if not output_dir.is_absolute():
            output_dir = root / output_dir
        try:
            publish_dir = output_dir.relative_to(root).as_posix()
        except ValueError:
            publish_dir = output_dir.as_posix()
        service_name = str(context.get("render_service_name") or "landing-page").strip()
        dry_run = bool(context.get("dry_run", True))
        html = template_path.read_text(encoding="utf-8").replace("__LANDING_CONFIG_URL__", landing_config_url)
        render_yaml = self._render_yaml(service_name, publish_dir)
        files = {
            output_dir / "index.html": html,
            output_dir / "render.yaml": render_yaml,
        }
        if not dry_run:
            output_dir.mkdir(parents=True, exist_ok=True)
            for path, content in files.items():
                path.write_text(content, encoding="utf-8")
        return {"ok": True, "data": {"template_type": template_type, "output_dir": str(output_dir), "files": [str(p) for p in files], "dry_run": dry_run}}

    def _render_yaml(self, service_name: str, publish_dir: str) -> str:
        return f"""services:
  - type: web
    name: {service_name}
    runtime: python
    buildCommand: python --version
    startCommand: python -m http.server $PORT --bind 0.0.0.0 --directory {publish_dir}
    pullRequestPreviewsEnabled: false
"""
