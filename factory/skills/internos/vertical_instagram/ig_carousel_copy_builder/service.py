from __future__ import annotations

import re


class IgCarouselCopyBuilderService:
    def ejecutar(self, context: dict) -> dict:
        if not isinstance(context, dict):
            return {"ok": False, "error": "context debe ser dict"}
        topic = str(context.get("topic") or "tema").strip()
        claims = context.get("claims")
        if not isinstance(claims, list):
            claims = []
        mode = str(context.get("mode") or "scientific").strip()
        primary = claims[0] if claims and isinstance(claims[0], dict) else {}
        secondary = claims[1] if len(claims) > 1 and isinstance(claims[1], dict) else {}
        slides = [
            {
                "kind": "cover",
                "layout_role": "cover",
                "headline": self._clip(topic, 70),
                "body": "Una guia breve para entender el tema sin exageraciones.",
            },
            {
                "kind": "body",
                "layout_role": "context",
                "headline": "Por que importa",
                "body": self._clip(primary.get("claim") or f"{topic} conecta habitos, contexto y respuesta individual.", 175),
                "evidence": primary.get("evidence_level") or "contextual",
                "source_title": primary.get("source_title") or "",
            },
            {
                "kind": "body",
                "layout_role": "mechanism",
                "headline": "Que pasa en el cuerpo",
                "body": self._clip(secondary.get("claim") or "El efecto depende del momento, la dosis, la constancia y la persona.", 175),
                "evidence": secondary.get("evidence_level") or "contextual",
                "source_title": secondary.get("source_title") or "",
            },
            {
                "kind": "body",
                "layout_role": "evidence",
                "headline": "Que dice la evidencia",
                "body": self._clip(self._evidence_summary(claims), 175),
                "evidence": "resumen",
                "source_title": self._source_summary(claims),
            },
            {
                "kind": "body",
                "layout_role": "application",
                "headline": "Como probarlo",
                "body": "Elige una variable, aplicala 7 dias y compara contra tu linea base. Sin prometer resultados universales.",
                "evidence": "aplicacion prudente",
                "source_title": "analisis editorial",
            },
            {
                "kind": "cta",
                "layout_role": "cta",
                "headline": "Usalo con criterio",
                "body": "Guarda la guia, revisa fuentes y convierte una idea en una accion medible.",
            },
        ]
        return {"ok": True, "data": {"slides": slides}}

    def _legacy_builder(self, context: dict, topic: str, claims: list, mode: str) -> dict:
        slides = [{"kind": "cover", "headline": self._clip(f"{topic}: guia clara y util", 70), "body": "Lo importante, lo aplicable y lo que no conviene exagerar."}]
        max_claim_slides = max(1, int(context.get("max_claim_slides") or 4))
        for claim in claims[:max_claim_slides]:
            if not isinstance(claim, dict):
                continue
            headline = self._clip(claim.get("claim") or "", 74)
            body = self._body(mode, claim)
            slides.append({"kind": "body", "headline": headline, "body": body, "evidence": claim.get("evidence_level"), "source_title": claim.get("source_title")})
        fillers = [
            {"headline": "Que observar antes de aplicarlo", "body": "Contexto, horario, constancia y respuesta individual importan tanto como el tip."},
            {"headline": "Donde suele fallar", "body": "El error comun es convertir un hallazgo puntual en una regla universal."},
            {"headline": "Como probarlo sin exagerar", "body": "Elige una variable, registra 7 dias y compara contra tu linea base."},
        ]
        for filler in fillers:
            if len(slides) >= 5:
                break
            slides.append({"kind": "body", **filler, "evidence": "contextual", "source_title": "analisis editorial"})
        slides.append({"kind": "cta", "headline": "Aplicalo con criterio", "body": "Guarda la guia, revisa fuentes y convierte una idea en una accion medible."})
        return {"ok": True, "data": {"slides": slides[:10]}}

    def _evidence_summary(self, claims: list) -> str:
        levels = []
        for claim in claims:
            if isinstance(claim, dict) and claim.get("evidence_level"):
                levels.append(str(claim["evidence_level"]))
        if not levels:
            return "La evidencia debe leerse por nivel de certeza, poblacion estudiada y limites."
        return "Las fuentes revisadas combinan evidencia " + ", ".join(levels[:3]) + ". Lo importante es no convertir un hallazgo en regla universal."

    def _source_summary(self, claims: list) -> str:
        sources = []
        for claim in claims:
            if isinstance(claim, dict) and claim.get("source_title"):
                sources.append(str(claim["source_title"]))
        return "; ".join(sources[:2])

    def _body(self, mode: str, claim: dict) -> str:
        evidence = claim.get("evidence_level") or "limitada"
        warning = claim.get("warning") or "Evita presentarlo como regla universal."
        if mode == "sales":
            return "Beneficio claro, objecion respondida y CTA directo."
        return self._clip(f"Evidencia {evidence}. {warning}", 180)

    def _clip(self, value: object, limit: int) -> str:
        text = re.sub(r"\s+", " ", str(value or "")).strip()
        return text if len(text) <= limit else text[: limit - 1].rstrip() + "..."
