from __future__ import annotations

import html
import json
import re
from base64 import b64encode
from pathlib import Path


class IgRenderCarouselSlidesService:
    def ejecutar(self, context: dict) -> dict:
        if not isinstance(context, dict):
            return {"ok": False, "error": "context debe ser dict"}
        template = context.get("template") if isinstance(context.get("template"), dict) else self._default_template(context)
        slides = self._slides(context)
        if not slides:
            return {"ok": False, "error": "slides o carousel requerido"}
        max_slides = int(context.get("max_slides") or 10)
        slides = slides[:max(1, min(max_slides, 10))]
        rendered = [self._render_slide(template, slide, idx, len(slides)) for idx, slide in enumerate(slides, start=1)]

        output_dir = context.get("output_dir")
        if output_dir and not context.get("dry_run", True):
            out = self._resolve_output_dir(output_dir)
            out.mkdir(parents=True, exist_ok=True)
            files = []
            for row in rendered:
                path = out / row["filename"]
                path.write_text(row["svg"], encoding="utf-8")
                files.append(str(path))
            manifest = {
                "template": template.get("name"),
                "format": "svg",
                "slides": [{"number": row["number"], "file": row["filename"], "headline": row["headline"]} for row in rendered],
            }
            (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=True, indent=2), encoding="utf-8")
            (out / "index.html").write_text(self._preview_html(rendered), encoding="utf-8")
            files.extend([str(out / "manifest.json"), str(out / "index.html")])
            return {"ok": True, "data": {"slides": rendered, "output_dir": str(out), "files": files}}
        return {"ok": True, "data": {"slides": rendered, "dry_run": True}}

    def _slides(self, context: dict) -> list[dict]:
        carousel = context.get("carousel") if isinstance(context.get("carousel"), dict) else {}
        raw = context.get("slides") if isinstance(context.get("slides"), list) else carousel.get("slides")
        slides = []
        cover = carousel.get("cover") if isinstance(carousel.get("cover"), dict) else None
        if cover:
            slides.append(
                {
                    "headline": cover.get("headline"),
                    "body": cover.get("subheadline"),
                    "kind": "cover",
                    "keyword": cover.get("keyword") or carousel.get("keyword") or context.get("keyword"),
                    "intent": cover.get("intent") or carousel.get("intent") or context.get("intent"),
                    "promise": cover.get("promise") or carousel.get("promise") or context.get("promise"),
                    "image_url": cover.get("image_url") or cover.get("image"),
                    "image_path": cover.get("image_path"),
                    "alt_text": cover.get("alt_text") or cover.get("alt"),
                }
            )
        for item in raw or []:
            if isinstance(item, dict):
                slides.append(
                    {
                        "headline": item.get("headline") or item.get("titulo") or item.get("title"),
                        "body": item.get("body") or item.get("cuerpo") or item.get("text"),
                        "kind": item.get("kind") or "body",
                        "evidence": item.get("evidence") or item.get("evidencia") or item.get("proof"),
                        "takeaway": item.get("takeaway") or item.get("conclusion") or item.get("accion"),
                        "keyword": item.get("keyword") or carousel.get("keyword") or context.get("keyword"),
                        "image_url": item.get("image_url") or item.get("image"),
                        "image_path": item.get("image_path"),
                        "alt_text": item.get("alt_text") or item.get("alt"),
                    }
                )
        cta = carousel.get("last_slide_cta") or context.get("last_slide_cta")
        if cta and slides:
            slides[-1]["body"] = f"{slides[-1].get('body') or ''}\n{cta}".strip()
            slides[-1]["kind"] = "cta"
        return [s for s in slides if str(s.get("headline") or s.get("body") or "").strip()]

    def _default_template(self, context: dict) -> dict:
        return {
            "name": "scientific_clean",
            "width": int(context.get("width") or 1080),
            "height": int(context.get("height") or 1350),
            "palette": {
                "background": "#f8fafc",
                "panel": "#ffffff",
                "ink": "#0f172a",
                "muted": "#475569",
                "accent": "#0f766e",
                "accent_2": "#2563eb",
                "line": "#cbd5e1",
            },
            "typography": {"font_family": "Arial, Helvetica, sans-serif", "headline_size": 76, "body_size": 38, "label_size": 24},
            "layout": {"margin": 72, "corner_radius": 22, "show_grid": True, "show_evidence_bar": True, "footer_label": "Fuente: sintesis educativa"},
        }

    def _render_slide(self, template: dict, slide: dict, number: int, total: int) -> dict:
        if template.get("style") == "seo_hero" or template.get("name") == "seo_hero":
            return self._render_seo_hero_slide(template, slide, number, total)
        width = int(template.get("width") or 1080)
        height = int(template.get("height") or 1350)
        palette = template.get("palette") if isinstance(template.get("palette"), dict) else {}
        typo = template.get("typography") if isinstance(template.get("typography"), dict) else {}
        layout = template.get("layout") if isinstance(template.get("layout"), dict) else {}
        margin = int(layout.get("margin") or 72)
        font = str(typo.get("font_family") or "Arial, Helvetica, sans-serif")
        headline = str(slide.get("headline") or "").strip()
        body = str(slide.get("body") or "").strip()
        accent = palette.get("accent", "#0f766e")
        accent_2 = palette.get("accent_2", "#2563eb")
        ink = palette.get("ink", "#0f172a")
        muted = palette.get("muted", "#475569")
        panel = palette.get("panel", "#ffffff")
        bg = palette.get("background", "#f8fafc")
        line = palette.get("line", "#cbd5e1")
        kind = str(slide.get("kind") or "body")
        head_size = int(typo.get("headline_size") or 76)
        body_size = int(typo.get("body_size") or 38)
        if kind == "cover":
            head_size += 8
        headline_lines = self._wrap(headline, 19 if kind == "cover" else 24, 4)
        body_lines = self._wrap(body, 34, 7)
        headline_svg = self._text_lines(headline_lines, margin + 36, 310, head_size, head_size + 10, ink, font, weight=800)
        body_svg = self._text_lines(body_lines, margin + 42, 650, body_size, body_size + 13, muted, font, weight=500)
        footer = html.escape(str(layout.get("footer_label") or "Fuente: sintesis educativa"))
        evidence_bar = ""
        if layout.get("show_evidence_bar", True):
            evidence_bar = f'<rect x="{margin}" y="{height - 210}" width="{width - margin * 2}" height="8" rx="4" fill="{html.escape(accent)}"/>'
        grid = ""
        if layout.get("show_grid", True):
            grid = "\n".join(
                f'<line x1="{x}" y1="0" x2="{x}" y2="{height}" stroke="{html.escape(line)}" stroke-width="1" opacity="0.22"/>'
                for x in range(margin, width, 180)
            )
        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="{width}" height="{height}" fill="{html.escape(bg)}"/>
  {grid}
  <rect x="{margin}" y="{margin}" width="{width - margin * 2}" height="{height - margin * 2}" rx="{int(layout.get('corner_radius') or 22)}" fill="{html.escape(panel)}" stroke="{html.escape(line)}" stroke-width="2"/>
  <circle cx="{width - margin - 48}" cy="{margin + 48}" r="30" fill="{html.escape(accent_2)}" opacity="0.18"/>
  <text x="{margin + 36}" y="{margin + 76}" font-family="{html.escape(font)}" font-size="24" font-weight="700" fill="{html.escape(accent)}">EVIDENCIA / {number:02d}</text>
  <text x="{width - margin - 36}" y="{margin + 76}" font-family="{html.escape(font)}" font-size="24" font-weight="700" text-anchor="end" fill="{html.escape(muted)}">{number}/{total}</text>
  {headline_svg}
  {body_svg}
  {evidence_bar}
  <text x="{margin + 36}" y="{height - margin - 44}" font-family="{html.escape(font)}" font-size="22" fill="{html.escape(muted)}">{footer}</text>
</svg>"""
        return {
            "number": number,
            "filename": f"slide_{number:02d}.svg",
            "headline": headline,
            "body": body,
            "svg": svg,
        }

    def _render_seo_hero_slide(self, template: dict, slide: dict, number: int, total: int) -> dict:
        width = int(template.get("width") or 1080)
        height = int(template.get("height") or 1350)
        palette = template.get("palette") if isinstance(template.get("palette"), dict) else {}
        typo = template.get("typography") if isinstance(template.get("typography"), dict) else {}
        layout = template.get("layout") if isinstance(template.get("layout"), dict) else {}
        margin = int(layout.get("margin") or 64)
        font = str(typo.get("font_family") or "Arial, Helvetica, sans-serif")
        headline = str(slide.get("headline") or "").strip()
        body = str(slide.get("body") or "").strip()
        keyword = str(slide.get("keyword") or "").strip()
        intent = str(slide.get("intent") or "educativo").strip()
        promise = str(slide.get("promise") or "aprende lo esencial en menos de un minuto").strip()
        evidence = str(slide.get("evidence") or "Sintesis basada en principios cientificos").strip()
        takeaway = str(slide.get("takeaway") or "").strip()
        image_href = self._image_href(slide.get("image_url") or slide.get("image_path"))
        alt_text = html.escape(str(slide.get("alt_text") or headline))
        kind = str(slide.get("kind") or "body")
        role = str(slide.get("layout_role") or kind).strip()
        accent = palette.get("accent", "#0b5fff")
        accent_2 = palette.get("accent_2", "#14b8a6")
        ink = palette.get("ink", "#101828")
        muted = palette.get("muted", "#475467")
        panel = palette.get("panel", "#ffffff")
        bg = palette.get("background", "#eef2f7")
        line = palette.get("line", "#d0d5dd")
        soft = palette.get("soft", "#e0f2fe")
        slide_typo = slide.get("typography") if isinstance(slide.get("typography"), dict) else {}
        head_size = min(int(slide_typo.get("headline_size") or typo.get("headline_size") or 42), 46 if kind == "cover" else 38)
        body_size = min(int(slide_typo.get("body_size") or typo.get("body_size") or 24), 24)
        footer = html.escape(str(layout.get("footer_label") or "Fuente: sintesis educativa"))
        hero_label = html.escape(str(layout.get("hero_label") or "GUIA SEO"))
        keyword_label = html.escape(str(layout.get("keyword_label") or "Keyword principal"))
        title_y = 392 if kind == "cover" else 382
        title_chars = 30 if kind == "cover" else 34
        title_lines = self._wrap(headline, title_chars, 3)
        body_lines = self._wrap(body, 44, 4)
        proof_lines = self._wrap(evidence, 38, 2)
        takeaway_lines = self._wrap(takeaway, 38, 2)
        title_svg = self._text_lines_centered(title_lines, width / 2, title_y, head_size, head_size + 12, ink, font, weight=900)
        body_svg = self._text_lines_centered(body_lines, width / 2, title_y + (len(title_lines) * (head_size + 12)) + 46, body_size, body_size + 11, muted, font, weight=500)
        proof_svg = self._text_lines(proof_lines, margin + 76, 894, 26, 36, ink, font, weight=700)
        takeaway_svg = self._text_lines(takeaway_lines, margin + 76, 1090, 27, 38, ink, font, weight=800) if takeaway else ""
        keyword_box = ""
        if keyword:
            keyword_box = f"""
  <rect x="{margin + 40}" y="170" width="{width - margin * 2 - 80}" height="56" rx="28" fill="{html.escape(soft)}" stroke="{html.escape(line)}"/>
  <text x="{margin + 68}" y="207" font-family="{html.escape(font)}" font-size="24" font-weight="800" fill="{html.escape(accent)}">{keyword_label}: {html.escape(keyword)}</text>"""
        role_label = {
            "cover": "GUIA",
            "context": "CONTEXTO",
            "mechanism": "MECANISMO",
            "evidence": "EVIDENCIA",
            "application": "APLICACION",
            "cta": "CIERRE",
        }.get(role, role.upper()[:16] or "SLIDE")
        source_note = ""
        if kind not in {"cover", "cta"}:
            source_text = self._wrap(str(slide.get("source_title") or evidence), 58, 2)
            source_svg = self._text_lines_centered(source_text, width / 2, 1052, 21, 30, muted, font, weight=600)
            source_note = f"""
  <rect x="{margin + 64}" y="990" width="{width - margin * 2 - 128}" height="118" rx="22" fill="{html.escape(soft)}" stroke="{html.escape(line)}" stroke-width="2"/>
  <text x="{width / 2}" y="1030" font-family="{html.escape(font)}" font-size="18" font-weight="900" text-anchor="middle" fill="{html.escape(accent)}">FUENTE / NOTA</text>
  {source_svg}"""
        image_block = ""
        if image_href:
            image_block = f"""
  <image href="{html.escape(image_href)}" x="{margin}" y="{margin}" width="{width - margin * 2}" height="{height - margin * 2}" opacity="0.20" preserveAspectRatio="xMidYMid slice">
    <title>{alt_text}</title>
  </image>
  <rect x="{margin}" y="{margin}" width="{width - margin * 2}" height="{height - margin * 2}" rx="{int(layout.get('corner_radius') or 18)}" fill="#ffffff" opacity="0.78"/>"""
        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="{width}" height="{height}" fill="{html.escape(bg)}"/>
  <rect x="{margin}" y="{margin}" width="{width - margin * 2}" height="{height - margin * 2}" rx="{int(layout.get('corner_radius') or 18)}" fill="{html.escape(panel)}" stroke="{html.escape(line)}" stroke-width="2"/>
  {image_block}
  <rect x="{margin}" y="{margin}" width="{width - margin * 2}" height="16" rx="8" fill="{html.escape(accent)}"/>
  <circle cx="{width - 172}" cy="238" r="118" fill="{html.escape(accent_2)}" opacity="0.11"/>
  <circle cx="{width - 110}" cy="310" r="62" fill="{html.escape(accent)}" opacity="0.10"/>
  <text x="{margin + 40}" y="{margin + 72}" font-family="{html.escape(font)}" font-size="24" font-weight="900" fill="{html.escape(accent)}">{html.escape(role_label)}</text>
  <text x="{width - margin - 40}" y="{margin + 72}" font-family="{html.escape(font)}" font-size="24" font-weight="800" text-anchor="end" fill="{html.escape(muted)}">{number}/{total}</text>
  {keyword_box}
  {title_svg}
  <text x="{width / 2}" y="310" font-family="{html.escape(font)}" font-size="21" font-weight="900" text-anchor="middle" fill="{html.escape(accent_2)}">INTENCION: {html.escape(intent.upper())}</text>
  {body_svg}
  {source_note}
  <text x="{margin + 40}" y="{height - margin - 42}" font-family="{html.escape(font)}" font-size="22" fill="{html.escape(muted)}">{footer}</text>
</svg>"""
        return {
            "number": number,
            "filename": f"slide_{number:02d}.svg",
            "headline": headline,
            "body": body,
            "svg": svg,
        }

    def _image_href(self, value: object) -> str:
        if not value:
            return ""
        raw = str(value)
        if raw.startswith(("http://", "https://", "data:")):
            return raw
        path = Path(raw)
        if not path.is_absolute():
            path = Path(__file__).resolve().parents[5] / path
        if not path.exists() or not path.is_file():
            return raw
        suffix = path.suffix.lower()
        mime = "image/svg+xml" if suffix == ".svg" else "image/png" if suffix == ".png" else "image/jpeg"
        encoded = b64encode(path.read_bytes()).decode("ascii")
        return f"data:{mime};base64,{encoded}"

    def _wrap(self, text: str, max_chars: int, max_lines: int) -> list[str]:
        words = re.sub(r"\s+", " ", text or "").strip().split(" ")
        lines: list[str] = []
        current = ""
        for word in words:
            candidate = word if not current else f"{current} {word}"
            if len(candidate) <= max_chars:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
            if len(lines) >= max_lines:
                break
        if current and len(lines) < max_lines:
            lines.append(current)
        return lines

    def _text_lines(self, lines: list[str], x: int, y: int, size: int, line_height: int, color: str, font: str, weight: int) -> str:
        return "\n".join(
            f'<text x="{x}" y="{y + idx * line_height}" font-family="{html.escape(font)}" font-size="{size}" font-weight="{weight}" fill="{html.escape(color)}">{html.escape(line)}</text>'
            for idx, line in enumerate(lines)
        )

    def _text_lines_centered(self, lines: list[str], x: float, y: int, size: int, line_height: int, color: str, font: str, weight: int) -> str:
        return "\n".join(
            f'<text x="{x:.0f}" y="{y + idx * line_height}" font-family="{html.escape(font)}" font-size="{size}" font-weight="{weight}" text-anchor="middle" fill="{html.escape(color)}">{html.escape(line)}</text>'
            for idx, line in enumerate(lines)
        )

    def _preview_html(self, rendered: list[dict]) -> str:
        body = "\n".join(f'<img src="{row["filename"]}" alt="Slide {row["number"]}"/>' for row in rendered)
        return f"""<!doctype html><html><head><meta charset="utf-8"/><style>body{{margin:24px;background:#e5e7eb;display:grid;gap:24px}}img{{width:360px;max-width:100%;box-shadow:0 12px 32px #0002}}</style></head><body>{body}</body></html>"""

    def _resolve_output_dir(self, value: str) -> Path:
        root = Path(__file__).resolve().parents[5]
        path = Path(str(value))
        if not path.is_absolute():
            path = root / path
        return path
