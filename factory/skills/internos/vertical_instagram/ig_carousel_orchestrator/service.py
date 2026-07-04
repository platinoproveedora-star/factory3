from __future__ import annotations

import importlib.util
import json
from pathlib import Path


class IgCarouselOrchestratorService:
    def ejecutar(self, context: dict) -> dict:
        if not isinstance(context, dict):
            return {"ok": False, "error": "context debe ser dict"}
        topic = str(context.get("topic") or "").strip()
        if not topic:
            return {"ok": False, "error": "topic requerido"}
        mode = str(context.get("mode") or "scientific").strip()
        output_dir = str(context.get("output_dir") or f"tmp/ig_carousel_orchestrated_{self._slug(topic)}")
        dry_run = bool(context.get("dry_run", True))
        steps = []
        warnings = []
        editorial_package = context.get("editorial_package") if isinstance(context.get("editorial_package"), dict) else {}
        claims = []

        if mode == "scientific":
            sources = context.get("sources") if isinstance(context.get("sources"), list) else []
            if sources:
                general_research = self._service("vertical_research", "research_general_essay", "ResearchGeneralEssayService").ejecutar(
                    {
                        "topic": topic,
                        "audience": context.get("audience") or "publico general",
                        "sources": sources,
                        "output_dir": f"{output_dir}/research",
                        "dry_run": dry_run,
                    }
                )
                steps.append({"skill": "vertical_research/research_general_essay", "ok": general_research.get("ok")})
                research = self._service("vertical_research", "research_topic_essay", "ResearchTopicEssayService").ejecutar(
                    {
                        "topic": context.get("specific_topic") or topic,
                        "parent_topic": topic,
                        "central_claim": context.get("central_claim") or topic,
                        "audience": context.get("audience") or "publico general",
                        "sources": sources,
                        "output_dir": f"{output_dir}/research",
                        "dry_run": dry_run,
                    }
                )
                steps.append({"skill": "vertical_research/research_topic_essay", "ok": research.get("ok")})
                if research.get("ok"):
                    editorial_package = research["data"]["essay"].get("editorial_package") or {}
            else:
                warnings.append("mode scientific sin sources: se omite research y no se inventa bibliografia")

        if editorial_package:
            claim_result = self._service("vertical_instagram", "ig_carousel_research_to_claims", "IgCarouselResearchToClaimsService").ejecutar(
                {"editorial_package": editorial_package}
            )
            steps.append({"skill": "vertical_instagram/ig_carousel_research_to_claims", "ok": claim_result.get("ok")})
            claims = (claim_result.get("data") or {}).get("claims") or []
        else:
            claims = context.get("claims") if isinstance(context.get("claims"), list) else []

        copy = self._service("vertical_instagram", "ig_carousel_copy_builder", "IgCarouselCopyBuilderService").ejecutar(
            {"topic": topic, "claims": claims, "mode": mode, "max_claim_slides": context.get("max_claim_slides") or 4}
        )
        steps.append({"skill": "vertical_instagram/ig_carousel_copy_builder", "ok": copy.get("ok")})
        if not copy.get("ok"):
            return {"ok": False, "error": copy.get("error"), "data": {"steps": steps, "warnings": warnings}}
        slides = copy["data"]["slides"]

        slides = self._service("vertical_instagram", "ig_carousel_layout_variants", "IgCarouselLayoutVariantsService").ejecutar(
            {"slides": slides, "mode": mode}
        )["data"]["slides"]
        slides = self._service("vertical_instagram", "ig_carousel_typography_fit", "IgCarouselTypographyFitService").ejecutar(
            {"slides": slides}
        )["data"]["slides"]
        image_assets = None
        if not dry_run:
            image_brief = self._service("vertical_instagram", "ig_carousel_image_brief", "IgCarouselImageBriefService").ejecutar(
                {"carousel": {"topic": topic, "cover": {"headline": slides[0].get("headline"), "subheadline": slides[0].get("body")}, "slides": slides[1:]}, "topic": topic}
            )
            steps.append({"skill": "vertical_instagram/ig_carousel_image_brief", "ok": image_brief.get("ok")})
            if image_brief.get("ok"):
                image_prompt = self._service("vertical_instagram", "ig_carousel_image_prompt", "IgCarouselImagePromptService").ejecutar(
                    {"brief": image_brief["data"]}
                )
                steps.append({"skill": "vertical_instagram/ig_carousel_image_prompt", "ok": image_prompt.get("ok")})
                image_assets = self._service("vertical_instagram", "ig_carousel_demo_image_assets", "IgCarouselDemoImageAssetsService").ejecutar(
                    {"image_briefs": image_brief["data"]["image_briefs"], "output_dir": f"{output_dir}/assets", "dry_run": False}
                )
                steps.append({"skill": "vertical_instagram/ig_carousel_demo_image_assets", "ok": image_assets.get("ok")})
                if image_assets.get("ok"):
                    assets_by_slide = {row.get("slide_number"): row for row in image_assets["data"].get("assets") or []}
                    for idx, slide in enumerate(slides, start=1):
                        asset = assets_by_slide.get(idx)
                        if asset:
                            slide["image_path"] = asset.get("path")
                            slide["alt_text"] = asset.get("alt_text")
        base_template = context.get("template")
        if not isinstance(base_template, dict):
            base_template = self._service("vertical_instagram", "ig_carousel_template_builder", "IgCarouselTemplateBuilderService").ejecutar(
                {"template_name": context.get("template_name") or "seo_hero", "dry_run": True}
            )["data"]["template"]
            steps.append({"skill": "vertical_instagram/ig_carousel_template_builder", "ok": True})
        theme = self._service("vertical_instagram", "ig_carousel_theme_guard", "IgCarouselThemeGuardService").ejecutar(
            {"theme": context.get("theme") or "teal_science", "template": base_template}
        )
        template = theme["data"]["template"]
        steps.extend(
            [
                {"skill": "vertical_instagram/ig_carousel_layout_variants", "ok": True},
                {"skill": "vertical_instagram/ig_carousel_typography_fit", "ok": True},
                {"skill": "vertical_instagram/ig_carousel_theme_guard", "ok": theme.get("ok")},
            ]
        )

        audit = self._service("vertical_instagram", "ig_carousel_slide_audit", "IgCarouselSlideAuditService").ejecutar(
            {"slides": slides, "template": template, "mode": mode}
        )
        steps.append({"skill": "vertical_instagram/ig_carousel_slide_audit", "ok": audit.get("ok")})
        if audit.get("ok") and not audit["data"].get("pass"):
            fixed = self._service("vertical_instagram", "ig_carousel_autofix_design", "IgCarouselAutofixDesignService").ejecutar(
                {"slides": slides, "template": template, "audit": audit["data"]}
            )
            steps.append({"skill": "vertical_instagram/ig_carousel_autofix_design", "ok": fixed.get("ok")})
            if fixed.get("ok"):
                slides = fixed["data"]["slides"]
                template = fixed["data"]["template"]

        rendered = None
        if not dry_run:
            rendered = self._service("vertical_instagram", "ig_render_carousel_slides", "IgRenderCarouselSlidesService").ejecutar(
                {"template": template, "carousel": {"cover": None, "slides": slides}, "slides": slides, "dry_run": False, "output_dir": output_dir}
            )
            steps.append({"skill": "vertical_instagram/ig_render_carousel_slides", "ok": rendered.get("ok")})
        manifest = {
            "slides": [{"number": idx, "headline": slide.get("headline"), "kind": slide.get("kind")} for idx, slide in enumerate(slides, start=1)]
        }
        report = self._service("vertical_instagram", "ig_carousel_quality_report", "IgCarouselQualityReportService").ejecutar(
            {"audit": audit.get("data"), "manifest": manifest, "output_path": f"{output_dir}/quality_report.json", "dry_run": dry_run}
        )
        steps.append({"skill": "vertical_instagram/ig_carousel_quality_report", "ok": report.get("ok")})
        data = {
            "topic": topic,
            "mode": mode,
            "slides": slides,
            "template": template,
            "audit": audit.get("data"),
            "quality_report": (report.get("data") or {}).get("report"),
            "rendered": rendered.get("data") if isinstance(rendered, dict) and rendered.get("ok") else None,
            "image_assets": image_assets.get("data") if isinstance(image_assets, dict) and image_assets.get("ok") else None,
            "steps": steps,
            "warnings": warnings,
        }
        if not dry_run:
            out = self._resolve_output_dir(output_dir)
            out.mkdir(parents=True, exist_ok=True)
            (out / "orchestrator_manifest.json").write_text(json.dumps(data, ensure_ascii=True, indent=2), encoding="utf-8")
            data["output_dir"] = str(out)
        return {"ok": True, "data": data}

    def _service(self, vertical: str, name: str, class_name: str):
        root = Path(__file__).resolve().parents[5]
        path = root / "factory" / "skills" / "internos" / vertical / name / "service.py"
        spec = importlib.util.spec_from_file_location(f"{vertical}_{name}_service", path)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        return getattr(module, class_name)()

    def _resolve_output_dir(self, value: str) -> Path:
        root = Path(__file__).resolve().parents[5]
        path = Path(value)
        if not path.is_absolute():
            path = root / path
        return path

    def _slug(self, value: str) -> str:
        return "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_")[:48] or "carousel"
