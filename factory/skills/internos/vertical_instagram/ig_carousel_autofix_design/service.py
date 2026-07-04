from __future__ import annotations

import re


class IgCarouselAutofixDesignService:
    def ejecutar(self, context: dict) -> dict:
        if not isinstance(context, dict):
            return {"ok": False, "error": "context debe ser dict"}
        slides = context.get("slides")
        if not isinstance(slides, list) or not slides:
            return {"ok": False, "error": "slides requerido"}
        fixed = []
        changes = []
        for idx, slide in enumerate(slides[:10], start=1):
            if not isinstance(slide, dict):
                continue
            row = dict(slide)
            headline = self._clean(row.get("headline") or row.get("title") or "")
            body = self._clean(row.get("body") or row.get("text") or "")
            if len(headline) > 82:
                row["headline"] = self._clip(headline, 82)
                changes.append({"slide": idx, "change": "headline recortado"})
            if len(body) > 190:
                row["body"] = self._clip(body, 190)
                changes.append({"slide": idx, "change": "body recortado"})
            row.setdefault("design_notes", [])
            row["design_notes"].append("autofix conservador aplicado")
            fixed.append(row)
        template = context.get("template") if isinstance(context.get("template"), dict) else {}
        palette = template.get("palette") if isinstance(template.get("palette"), dict) else {}
        if str(palette.get("ink", "")).lower() in {"#000", "#000000", "black"}:
            template = {**template, "palette": {**palette, "ink": "#12343b", "muted": "#48666b"}}
            changes.append({"template": "palette", "change": "negro puro reemplazado"})
        return {"ok": True, "data": {"slides": fixed, "template": template, "changes": changes}}

    def _clean(self, value: object) -> str:
        return re.sub(r"\s+", " ", str(value or "")).strip()

    def _clip(self, value: str, limit: int) -> str:
        return value if len(value) <= limit else value[: limit - 1].rstrip() + "..."
