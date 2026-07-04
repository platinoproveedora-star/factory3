from __future__ import annotations

import re


class IgCarouselSlideAuditService:
    def ejecutar(self, context: dict) -> dict:
        if not isinstance(context, dict):
            return {"ok": False, "error": "context debe ser dict"}
        slides = context.get("slides")
        if not isinstance(slides, list) or not slides:
            return {"ok": False, "error": "slides requerido"}
        template = context.get("template") if isinstance(context.get("template"), dict) else {}
        palette = template.get("palette") if isinstance(template.get("palette"), dict) else {}
        results = []
        for idx, slide in enumerate(slides[:10], start=1):
            if not isinstance(slide, dict):
                continue
            warnings = []
            headline = self._clean(slide.get("headline") or slide.get("title") or "")
            body = self._clean(slide.get("body") or slide.get("text") or "")
            kind = str(slide.get("kind") or "").lower()
            if len(headline) > 82:
                warnings.append("headline largo; riesgo de desborde o letra pequena")
            if len(body) > 190:
                warnings.append("body largo; dividir o recortar")
            if kind not in {"cover", "cta"} and not (slide.get("evidence") or slide.get("source_title")) and context.get("mode") == "scientific":
                warnings.append("slide cientifica sin evidencia/fuente asociada")
            if str(palette.get("ink", "")).lower() in {"#000", "#000000", "black"}:
                warnings.append("tinta negra pura no recomendada para este tema")
            density = len(headline) + len(body)
            score = max(40, 100 - len(warnings) * 12 - max(0, density - 220) // 10)
            results.append({"slide_number": idx, "score": score, "warnings": warnings, "density": density})
        average = round(sum(r["score"] for r in results) / len(results), 2) if results else 0
        return {"ok": True, "data": {"average_score": average, "slides": results, "pass": average >= 80 and all(not r["warnings"] for r in results)}}

    def _clean(self, value: object) -> str:
        return re.sub(r"\s+", " ", str(value or "")).strip()
