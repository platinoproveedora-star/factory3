from __future__ import annotations

import json
from pathlib import Path


class IgCarouselExportAssetsService:
    def ejecutar(self, context: dict) -> dict:
        if not isinstance(context, dict):
            return {"ok": False, "error": "context debe ser dict"}
        slides = context.get("slides")
        if not isinstance(slides, list) or not slides:
            return {"ok": False, "error": "slides requerido"}
        output_dir = context.get("output_dir")
        if not output_dir:
            return {"ok": False, "error": "output_dir requerido"}
        out = self._resolve_output_dir(str(output_dir))
        manifest = {
            "format": "svg",
            "asset_count": len(slides),
            "slides": [],
            "caption": context.get("caption") or "",
            "hashtags": context.get("hashtags") or [],
        }
        planned_files = []
        for idx, slide in enumerate(slides, start=1):
            if not isinstance(slide, dict) or not slide.get("svg"):
                continue
            filename = str(slide.get("filename") or f"slide_{idx:02d}.svg")
            planned_files.append(str(out / filename))
            manifest["slides"].append({"number": idx, "file": filename, "headline": slide.get("headline") or ""})
        if context.get("dry_run", True):
            return {
                "ok": True,
                "message": "dry_run: no se exportaron assets",
                "data": {"manifest": manifest, "output_dir": str(out), "files": planned_files, "dry_run": True},
            }
        out.mkdir(parents=True, exist_ok=True)
        files = []
        for idx, slide in enumerate(slides, start=1):
            if not isinstance(slide, dict) or not slide.get("svg"):
                continue
            filename = str(slide.get("filename") or f"slide_{idx:02d}.svg")
            path = out / filename
            path.write_text(str(slide["svg"]), encoding="utf-8")
            files.append(str(path))
        (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=True, indent=2), encoding="utf-8")
        (out / "index.html").write_text(self._preview_html(manifest["slides"]), encoding="utf-8")
        files.extend([str(out / "manifest.json"), str(out / "index.html")])
        return {"ok": True, "data": {"output_dir": str(out), "files": files, "manifest": manifest}}

    def _preview_html(self, slides: list[dict]) -> str:
        imgs = "\n".join(f'<img src="{row["file"]}" alt="Slide {row["number"]}"/>' for row in slides)
        return f"""<!doctype html><html><head><meta charset="utf-8"/><style>body{{margin:24px;background:#e5e7eb;display:grid;gap:24px}}img{{width:360px;max-width:100%;box-shadow:0 12px 32px #0002}}</style></head><body>{imgs}</body></html>"""

    def _resolve_output_dir(self, value: str) -> Path:
        root = Path(__file__).resolve().parents[5]
        path = Path(value)
        if not path.is_absolute():
            path = root / path
        return path
