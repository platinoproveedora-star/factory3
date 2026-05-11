"""Escanea disco y agrega al registry los skills que faltan."""
from __future__ import annotations

import json
from pathlib import Path

_SKILLS_ROOT = Path(__file__).parent.parent.parent  # factory/skills/
_FOLDERS     = ["internos", "meta", "eval"]
_TIPO_MAP    = {"internos": "interno", "meta": "meta", "eval": "eval"}


class SkillRegistrySyncService:

    def ejecutar(self, context: dict) -> dict:
        folders  = context.get("folders") or _FOLDERS
        dry_run  = context.get("dry_run", True)

        registry = self._cargar_registry()
        en_disco  = self._escanear(folders)

        agregados   = []
        ya_existen  = []

        for folder, skill_dir in en_disco:
            name = skill_dir.name
            if name in registry:
                ya_existen.append(name)
                continue

            manifest = self._leer_manifest(skill_dir)
            entry = {
                "tipo":        _TIPO_MAP.get(folder, "interno"),
                "nombre":      name,
                "vertical":    manifest.get("vertical", "factory"),
                "descripcion": manifest.get("description", f"Skill {name}"),
                "path":        f"skills/{folder}/{name}",
                "entrypoint":  manifest.get("entrypoint", "skill.py"),
                "version":     manifest.get("version", "0.1.0"),
            }
            if manifest.get("kind") == "data":
                entry["kind"] = "data"

            registry[name] = entry
            agregados.append({"nombre": name, "folder": folder, "entry": entry})

        if agregados and not dry_run:
            registry_path = _SKILLS_ROOT / "registry.json"
            registry_path.write_text(
                json.dumps(registry, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

        return {
            "ok": True,
            "message": (
                f"{'[dry_run] ' if dry_run else ''}"
                f"{len(agregados)} agregados · {len(ya_existen)} ya existían"
            ),
            "data": {
                "dry_run":      dry_run,
                "agregados":    len(agregados),
                "ya_existen":   len(ya_existen),
                "total_disco":  len(en_disco),
                "detalle":      agregados,
            },
        }

    def _escanear(self, folders: list) -> list:
        encontrados = []
        for folder in folders:
            p = _SKILLS_ROOT / folder
            if not p.exists():
                continue
            for skill_dir in sorted(p.iterdir()):
                if skill_dir.is_dir() and not skill_dir.name.startswith(("_", ".")):
                    if (skill_dir / "skill.py").exists():
                        encontrados.append((folder, skill_dir))
        return encontrados

    def _leer_manifest(self, skill_dir: Path) -> dict:
        m = skill_dir / "manifest.json"
        if not m.exists():
            return {}
        try:
            return json.loads(m.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _cargar_registry(self) -> dict:
        p = _SKILLS_ROOT / "registry.json"
        if not p.exists():
            return {}
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}
