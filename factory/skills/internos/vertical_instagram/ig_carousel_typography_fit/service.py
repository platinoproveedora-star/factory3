from __future__ import annotations

import re


class IgCarouselTypographyFitService:
    def ejecutar(self, context: dict) -> dict:
        if not isinstance(context, dict):
            return {"ok": False, "error": "context debe ser dict"}
        slides = context.get("slides")
        if not isinstance(slides, list) or not slides:
            return {"ok": False, "error": "slides requerido"}
        fitted = []
        for idx, slide in enumerate(slides[:10], start=1):
            if not isinstance(slide, dict):
                continue
            headline = self._clean(slide.get("headline") or slide.get("title") or "")
            body = self._clean(slide.get("body") or slide.get("text") or "")
            kind = str(slide.get("kind") or ("cover" if idx == 1 else "body"))
            headline_size = self._size(len(headline), 54 if kind == "cover" else 44, 30)
            body_size = self._size(len(body), 27, 20)
            fitted.append(
                {
                    **slide,
                    "typography": {
                        "headline_size": headline_size,
                        "body_size": body_size,
                        "max_headline_chars": 70 if kind == "cover" else 82,
                        "max_body_chars": 180,
                        "headline_risk": len(headline) > (70 if kind == "cover" else 82),
                        "body_risk": len(body) > 180,
                    },
                }
            )
        return {"ok": True, "data": {"slides": fitted}}

    def _size(self, chars: int, max_size: int, min_size: int) -> int:
        if chars <= 45:
            return max_size
        if chars >= 130:
            return min_size
        return max(min_size, max_size - int((chars - 45) / 5))

    def _clean(self, value: object) -> str:
        return re.sub(r"\s+", " ", str(value or "")).strip()
