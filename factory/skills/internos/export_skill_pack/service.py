"""Service for export_skill_pack - exports skills grouped by vertical."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

_VALID_NAME = re.compile(r"^[a-z][a-z0-9_-]*$")


class ExportSkillPackService:

    def ejecutar(self, context: dict) -> dict:
        ok, error = self._validar(context)
        if not ok:
            return {"ok": False, "error": error}

        base_dir = Path(context.get("base_dir", "factory"))
        vertical = context["vertical"]
        registry_path = base_dir / "skills" / "registry.json"
        registry = self._load_json(registry_path)
        selected = {
            name: entry
            for name, entry in registry.items()
            if isinstance(entry, dict) and entry.get("vertical") == vertical
        }
        if not selected:
            return {"ok": False, "error": f"no hay skills para vertical: {vertical}"}

        output_root = Path(context.get("output_dir", "exports/skill_packs"))
        pack_name = context.get("pack_name") or vertical
        pack_dir = output_root / pack_name
        plan = self._plan(base_dir, pack_dir, vertical, selected)

        if context.get("dry_run", True):
            return {"ok": True, "message": "plan de export generado; no se escribio nada", "data": plan}

        if pack_dir.exists() and not context.get("overwrite", False):
            return {"ok": False, "error": f"pack ya existe: {pack_dir}", "data": plan}
        if pack_dir.exists():
            shutil.rmtree(pack_dir)

        skills_dir = pack_dir / "skills" / "internos"
        skills_dir.mkdir(parents=True, exist_ok=True)
        exported_registry = {}
        for name, entry in selected.items():
            source_path = base_dir / entry.get("path", f"skills/internos/{name}")
            target_path = skills_dir / name
            if not source_path.exists():
                return {"ok": False, "error": f"skill path no existe: {source_path}", "data": plan}
            shutil.copytree(source_path, target_path, ignore=shutil.ignore_patterns("__pycache__"))
            exported_registry[name] = entry

        (pack_dir / "skills").mkdir(exist_ok=True)
        self._write_json(pack_dir / "skills" / "registry.json", exported_registry)
        self._write_json(
            pack_dir / "pack_manifest.json",
            {
                "type": "skill_pack",
                "name": pack_name,
                "vertical": vertical,
                "skills": sorted(exported_registry),
                "count": len(exported_registry),
            },
        )
        return {"ok": True, "message": "skill pack exportado", "data": plan}

    def _validar(self, context: dict) -> tuple[bool, str | None]:
        vertical = context.get("vertical")
        if not isinstance(vertical, str) or not _VALID_NAME.match(vertical):
            return False, "vertical es requerida y debe usar letras, numeros, _ o -"
        pack_name = context.get("pack_name")
        if pack_name and (not isinstance(pack_name, str) or not _VALID_NAME.match(pack_name)):
            return False, "pack_name debe usar letras, numeros, _ o -"
        if not isinstance(context.get("dry_run", True), bool):
            return False, "dry_run debe ser booleano"
        if not isinstance(context.get("overwrite", False), bool):
            return False, "overwrite debe ser booleano"
        return True, None

    def _plan(self, base_dir: Path, pack_dir: Path, vertical: str, selected: dict) -> dict:
        return {
            "vertical": vertical,
            "base_dir": str(base_dir),
            "pack_dir": str(pack_dir),
            "skills": sorted(selected),
            "count": len(selected),
            "files": [
                str(pack_dir / "skills" / "internos" / name)
                for name in sorted(selected)
            ],
        }

    def _load_json(self, path: Path) -> dict:
        if not path.exists():
            return {}
        raw = path.read_text(encoding="utf-8-sig", errors="replace").strip()
        if not raw:
            return {}
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}

    def _write_json(self, path: Path, data: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
