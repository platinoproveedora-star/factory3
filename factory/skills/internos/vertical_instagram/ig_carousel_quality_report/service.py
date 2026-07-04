from __future__ import annotations

import json
from pathlib import Path


class IgCarouselQualityReportService:
    def ejecutar(self, context: dict) -> dict:
        if not isinstance(context, dict):
            return {"ok": False, "error": "context debe ser dict"}
        audit = context.get("audit") if isinstance(context.get("audit"), dict) else {}
        manifest = context.get("manifest") if isinstance(context.get("manifest"), dict) else {}
        score = float(audit.get("average_score") or 0)
        warnings = []
        for row in audit.get("slides") or []:
            if isinstance(row, dict):
                for warning in row.get("warnings") or []:
                    warnings.append({"slide": row.get("slide_number"), "warning": warning})
        report = {
            "score": score,
            "status": "ready" if score >= 85 and not warnings else "needs_review",
            "warnings": warnings,
            "slide_count": len(manifest.get("slides") or []),
            "checks": {
                "audit_present": bool(audit),
                "manifest_present": bool(manifest),
                "warnings_count": len(warnings),
            },
        }
        output_path = context.get("output_path")
        if output_path and not context.get("dry_run", True):
            path = self._resolve_output_path(str(output_path))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(report, ensure_ascii=True, indent=2), encoding="utf-8")
            return {"ok": True, "data": {"report": report, "file": str(path)}}
        return {"ok": True, "data": {"report": report, "dry_run": True}}

    def _resolve_output_path(self, value: str) -> Path:
        root = Path(__file__).resolve().parents[5]
        path = Path(value)
        if not path.is_absolute():
            path = root / path
        return path
