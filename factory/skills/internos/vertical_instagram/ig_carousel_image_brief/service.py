from __future__ import annotations


class IgCarouselImageBriefService:
    def ejecutar(self, context: dict) -> dict:
        if not isinstance(context, dict):
            return {"ok": False, "error": "context debe ser dict"}
        carousel = context.get("carousel") if isinstance(context.get("carousel"), dict) else {}
        slides = context.get("slides") if isinstance(context.get("slides"), list) else carousel.get("slides")
        cover = carousel.get("cover") if isinstance(carousel.get("cover"), dict) else None
        if not isinstance(slides, list) or not slides:
            return {"ok": False, "error": "slides requerido"}
        topic = str(context.get("topic") or carousel.get("topic") or carousel.get("keyword") or "tema educativo").strip()
        style = str(context.get("visual_style") or "infografia editorial cientifica").strip()
        audience = str(context.get("audience") or carousel.get("audience") or "audiencia general").strip()
        image_briefs = []
        source_slides = []
        if cover:
            source_slides.append(
                {
                    "headline": cover.get("headline") or topic,
                    "body": cover.get("subheadline") or carousel.get("promise") or "",
                    "kind": "cover",
                }
            )
        source_slides.extend(slides)
        for idx, slide in enumerate(source_slides[:10], start=1):
            if not isinstance(slide, dict):
                continue
            headline = str(slide.get("headline") or slide.get("title") or f"Slide {idx}").strip()
            evidence = str(slide.get("evidence") or slide.get("body") or "").strip()
            image_briefs.append(
                {
                    "slide_number": idx,
                    "headline": headline,
                    "image_role": "hero visual" if slide.get("kind") == "cover" or idx == 1 else "supporting infographic",
                    "subject": self._subject(topic, headline),
                    "composition": self._composition(idx),
                    "must_show": [topic, headline],
                    "avoid": ["texto pequeno ilegible", "logos reales", "claims medicos absolutos", "personas identificables sin permiso"],
                    "alt_text": f"Infografia sobre {headline} para {audience}.",
                    "evidence_hint": evidence[:180],
                    "visual_style": style,
                }
            )
        return {"ok": True, "data": {"topic": topic, "audience": audience, "image_briefs": image_briefs}}

    def _subject(self, topic: str, headline: str) -> str:
        return f"{topic}: {headline}".strip(": ")

    def _composition(self, idx: int) -> str:
        if idx == 1:
            return "imagen protagonista a la derecha, titular fuerte a la izquierda, profundidad ligera"
        if idx % 2 == 0:
            return "diagrama central con 3 elementos conectados y espacio limpio para texto"
        return "visual comparativo antes/despues con iconos simples y fondo claro"
