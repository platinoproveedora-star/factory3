from __future__ import annotations


class IgCarouselLayoutVariantsService:
    def ejecutar(self, context: dict) -> dict:
        if not isinstance(context, dict):
            return {"ok": False, "error": "context debe ser dict"}
        slides = context.get("slides")
        if not isinstance(slides, list) or not slides:
            return {"ok": False, "error": "slides requerido"}
        mode = str(context.get("mode") or "scientific").strip()
        variants = []
        total = len(slides)
        for idx, slide in enumerate(slides[:10], start=1):
            if not isinstance(slide, dict):
                continue
            variant = self._variant(idx, total, slide, mode)
            variants.append({**slide, "layout_variant": variant})
        return {"ok": True, "data": {"mode": mode, "slides": variants}}

    def _variant(self, idx: int, total: int, slide: dict, mode: str) -> str:
        kind = str(slide.get("kind") or "").lower()
        text = f"{slide.get('headline') or ''} {slide.get('body') or ''}".lower()
        if idx == 1 or kind == "cover":
            return "cover_hero"
        if idx == total or kind == "cta":
            return "cta_summary"
        if "mito" in text or "vs" in text:
            return "myth_vs_reality"
        if "paso" in text or mode == "how_to":
            return "process_steps"
        if "evidencia" in text or mode == "scientific":
            return "claim_evidence_takeaway"
        return "image_text_split"
