from __future__ import annotations

import html
import json
import re
from pathlib import Path


class IgCarouselDemoImageAssetsService:
    def ejecutar(self, context: dict) -> dict:
        if not isinstance(context, dict):
            return {"ok": False, "error": "context debe ser dict"}
        briefs = context.get("image_briefs")
        if not isinstance(briefs, list) or not briefs:
            return {"ok": False, "error": "image_briefs requerido"}
        output_dir = context.get("output_dir")
        if not output_dir:
            return {"ok": False, "error": "output_dir requerido"}
        out = self._resolve_output_dir(str(output_dir))
        assets = []
        for idx, brief in enumerate(briefs[:10], start=1):
            if not isinstance(brief, dict):
                continue
            filename = f"image_{idx:02d}.svg"
            path = out / filename
            assets.append(
                {
                    "slide_number": brief.get("slide_number") or idx,
                    "file": filename,
                    "path": str(path),
                    "alt_text": brief.get("alt_text") or "",
                    "svg": self._svg(idx, str(brief.get("headline") or ""), str(brief.get("subject") or "")),
                }
            )
        if context.get("dry_run", True):
            return {"ok": True, "data": {"assets": assets, "output_dir": str(out), "dry_run": True}}
        out.mkdir(parents=True, exist_ok=True)
        for asset in assets:
            Path(asset["path"]).write_text(asset["svg"], encoding="utf-8")
        (out / "manifest.json").write_text(json.dumps({"assets": assets}, ensure_ascii=True, indent=2), encoding="utf-8")
        return {"ok": True, "data": {"assets": assets, "output_dir": str(out)}}

    def _svg(self, idx: int, headline: str, subject: str) -> str:
        colors = [("#7fcac3", "#d9f0ed"), ("#89b7d6", "#e2eef6"), ("#9cc9a8", "#ecf6ee"), ("#b9c7db", "#f0f4f8")]
        accent, accent_2 = colors[(idx - 1) % len(colors)]
        title = html.escape(self._clip(headline, 34))
        sub = html.escape(self._clip(subject, 52))
        return f"""<svg xmlns="http://www.w3.org/2000/svg" width="720" height="720" viewBox="0 0 720 720">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{accent}" stop-opacity="0.95"/>
      <stop offset="1" stop-color="{accent_2}" stop-opacity="0.85"/>
    </linearGradient>
  </defs>
  <rect width="720" height="720" rx="42" fill="#f7fbfb"/>
  <rect x="44" y="44" width="632" height="632" rx="38" fill="url(#g)" opacity="0.74"/>
  <circle cx="560" cy="168" r="124" fill="#ffffff" opacity="0.24"/>
  <circle cx="170" cy="544" r="152" fill="#ffffff" opacity="0.22"/>
  <circle cx="360" cy="360" r="188" fill="#ffffff" opacity="0.10"/>
  <path d="M124 430 C218 286 318 486 424 324 S548 368 596 220" fill="none" stroke="#ffffff" stroke-width="12" stroke-linecap="round" opacity="0.42"/>
  <path d="M128 274 L236 274 L290 210 L372 430 L438 318 L590 318" fill="none" stroke="#ffffff" stroke-width="10" stroke-linecap="round" stroke-linejoin="round" opacity="0.34"/>
  <rect x="98" y="104" width="166" height="14" rx="7" fill="#ffffff" opacity="0.30"/>
  <rect x="98" y="132" width="254" height="12" rx="6" fill="#ffffff" opacity="0.18"/>
  <rect x="98" y="590" width="330" height="12" rx="6" fill="#ffffff" opacity="0.16"/>
</svg>"""

    def _clip(self, value: str, limit: int) -> str:
        value = re.sub(r"\s+", " ", value).strip()
        return value if len(value) <= limit else value[: limit - 1].rstrip() + "..."

    def _resolve_output_dir(self, value: str) -> Path:
        root = Path(__file__).resolve().parents[5]
        path = Path(value)
        if not path.is_absolute():
            path = root / path
        return path
