"""Service for list_skills_by_vertical - groups registry skills by vertical."""

from __future__ import annotations

import json
from pathlib import Path


class ListSkillsByVerticalService:

    def ejecutar(self, context: dict) -> dict:
        base_dir = Path(context.get("base_dir", "factory"))
        registry_path = base_dir / "skills" / "registry.json"
        registry = self._load_registry(registry_path)
        if not registry:
            return {"ok": True, "message": "sin skills registrados", "data": {"verticals": {}}}

        verticals: dict[str, list[dict]] = {}
        for name, entry in registry.items():
            if not isinstance(entry, dict):
                continue
            vertical = entry.get("vertical", "sin_vertical")
            verticals.setdefault(vertical, []).append(
                {
                    "name": name,
                    "description": entry.get("descripcion", ""),
                    "path": entry.get("path", ""),
                }
            )

        for skills in verticals.values():
            skills.sort(key=lambda item: item["name"])

        ordered = dict(sorted(verticals.items(), key=lambda item: item[0]))
        return {
            "ok": True,
            "message": "skills agrupados por vertical",
            "data": {
                "registry_path": str(registry_path),
                "verticals": ordered,
                "counts": {vertical: len(skills) for vertical, skills in ordered.items()},
            },
        }

    def _load_registry(self, path: Path) -> dict:
        if not path.exists():
            return {}
        raw = path.read_text(encoding="utf-8-sig", errors="replace").strip()
        if not raw:
            return {}
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}
