from __future__ import annotations


class IgCarouselResearchToClaimsService:
    def ejecutar(self, context: dict) -> dict:
        if not isinstance(context, dict):
            return {"ok": False, "error": "context debe ser dict"}
        package = context.get("editorial_package") if isinstance(context.get("editorial_package"), dict) else {}
        essay = context.get("essay") if isinstance(context.get("essay"), dict) else {}
        claims = package.get("safe_claims") if isinstance(package.get("safe_claims"), list) else essay.get("claims_for_carousel")
        if not isinstance(claims, list) or not claims:
            return {"ok": False, "error": "claims/editorial_package requerido"}
        rows = []
        for idx, item in enumerate(claims[:8], start=1):
            if not isinstance(item, dict):
                continue
            text = item.get("carousel_version") or item.get("claim") or ""
            rows.append(
                {
                    "claim_id": f"claim_{idx:02d}",
                    "claim": text,
                    "source_title": item.get("source_title") or "",
                    "evidence_level": item.get("evidence_level") or "limitada",
                    "warning": item.get("warning") or "",
                    "slide_hint": item.get("slide_hint") or f"claim {idx}",
                }
            )
        return {"ok": True, "data": {"claims": rows}}
