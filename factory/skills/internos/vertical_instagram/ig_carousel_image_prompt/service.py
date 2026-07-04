from __future__ import annotations


class IgCarouselImagePromptService:
    def ejecutar(self, context: dict) -> dict:
        if not isinstance(context, dict):
            return {"ok": False, "error": "context debe ser dict"}
        briefs = context.get("image_briefs")
        if not isinstance(briefs, list):
            data = context.get("brief") if isinstance(context.get("brief"), dict) else {}
            briefs = data.get("image_briefs")
        if not isinstance(briefs, list) or not briefs:
            return {"ok": False, "error": "image_briefs requerido"}
        brand_style = str(context.get("brand_style") or "clean scientific editorial, premium Instagram carousel, 4:5").strip()
        prompts = []
        for item in briefs[:10]:
            if not isinstance(item, dict):
                continue
            prompt = (
                f"{brand_style}. Create an infographic image for slide {item.get('slide_number')}: "
                f"{item.get('subject')}. Composition: {item.get('composition')}. "
                f"Visual role: {item.get('image_role')}. Style: {item.get('visual_style')}. "
                "No tiny text, no logos, no watermark, no realistic brand marks. Leave clean negative space for Spanish overlay text."
            )
            prompts.append(
                {
                    "slide_number": item.get("slide_number"),
                    "headline": item.get("headline"),
                    "prompt": prompt,
                    "negative_prompt": ", ".join(item.get("avoid") or []),
                    "alt_text": item.get("alt_text") or "",
                }
            )
        return {"ok": True, "data": {"prompts": prompts}}
