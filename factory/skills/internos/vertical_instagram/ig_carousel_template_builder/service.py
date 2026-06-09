from __future__ import annotations

import json
from pathlib import Path


_PALETTES = {
    "clinical": {
        "background": "#f8fafc",
        "panel": "#ffffff",
        "ink": "#0f172a",
        "muted": "#475569",
        "accent": "#0f766e",
        "accent_2": "#2563eb",
        "line": "#cbd5e1",
    },
    "lab": {
        "background": "#f5f7fb",
        "panel": "#ffffff",
        "ink": "#111827",
        "muted": "#4b5563",
        "accent": "#1d4ed8",
        "accent_2": "#7c3aed",
        "line": "#d1d5db",
    },
    "journal": {
        "background": "#fbfbf8",
        "panel": "#ffffff",
        "ink": "#1f2937",
        "muted": "#52525b",
        "accent": "#b45309",
        "accent_2": "#0f766e",
        "line": "#d6d3d1",
    },
}


class IgCarouselTemplateBuilderService:
    def ejecutar(self, context: dict) -> dict:
        if not isinstance(context, dict):
            return {"ok": False, "error": "context debe ser dict"}
        name = str(context.get("template_name") or context.get("name") or "scientific_clean").strip()
        palette_name = str(context.get("palette") or "clinical").strip()
        palette = dict(_PALETTES.get(palette_name) or _PALETTES["clinical"])
        palette.update(context.get("colors") if isinstance(context.get("colors"), dict) else {})

        ratio = str(context.get("ratio") or "4:5").strip()
        width, height = (1080, 1080) if ratio == "1:1" else (1080, 1350)
        template = {
            "name": name,
            "style": "scientific",
            "ratio": ratio,
            "width": width,
            "height": height,
            "palette": palette,
            "typography": {
                "font_family": str(context.get("font_family") or "Arial, Helvetica, sans-serif"),
                "headline_size": int(context.get("headline_size") or 76),
                "body_size": int(context.get("body_size") or 38),
                "label_size": int(context.get("label_size") or 24),
            },
            "layout": {
                "margin": 72,
                "corner_radius": 22,
                "show_grid": bool(context.get("show_grid", True)),
                "show_evidence_bar": bool(context.get("show_evidence_bar", True)),
                "footer_label": str(context.get("footer_label") or "Fuente: sintesis educativa"),
            },
            "slides": {
                "cover": "large_hypothesis",
                "body": "claim_evidence",
                "cta": "summary_action",
            },
        }

        output_path = context.get("output_path")
        if output_path and not context.get("dry_run", True):
            path = self._resolve_output_path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(template, ensure_ascii=True, indent=2), encoding="utf-8")
            return {"ok": True, "data": {"template": template, "file": str(path)}}
        return {"ok": True, "data": {"template": template}}

    def _resolve_output_path(self, value: str) -> Path:
        root = Path(__file__).resolve().parents[5]
        path = Path(str(value))
        if not path.is_absolute():
            path = root / path
        return path
