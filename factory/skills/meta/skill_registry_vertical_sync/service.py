"""Escanea skills/internos/vertical_*/<skill>/ y agrega al registry los que falten."""
from __future__ import annotations

import json
from pathlib import Path

_SKILLS_ROOT = Path(__file__).parent.parent.parent  # factory/skills/
_INTERNOS = "internos"


class SkillRegistryVerticalSyncService:

    def ejecutar(self, context: dict) -> dict:
        dry_run = context.get("dry_run", True)
        vertical_filter = str(context.get("vertical") or "").strip() or None

        registry = self._cargar_registry()
        en_disco = self._escanear(vertical_filter)

        agregados = []
        ya_existen = []

        for vertical_dir, skill_dir in en_disco:
            name = f"{vertical_dir.name}/{skill_dir.name}"
            if name in registry:
                ya_existen.append(name)
                continue

            manifest = self._leer_manifest(skill_dir)
            entry = {
                "tipo": "interno",
                "nombre": name,
                "vertical": vertical_dir.name,
                "descripcion": manifest.get("description", f"Skill {name}"),
                "path": f"skills/{_INTERNOS}/{vertical_dir.name}/{skill_dir.name}",
                "entrypoint": manifest.get("entrypoint", "skill.py"),
                "version": manifest.get("version", "0.1.0"),
            }
            if manifest.get("kind") == "data":
                entry["kind"] = "data"

            registry[name] = entry
            agregados.append({"nombre": name, "vertical": vertical_dir.name, "entry": entry})

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
                "dry_run": dry_run,
                "agregados": len(agregados),
                "ya_existen": len(ya_existen),
                "total_disco": len(en_disco),
                "detalle": agregados,
            },
        }

    def _escanear(self, vertical_filter: str | None) -> list:
        encontrados = []
        internos_root = _SKILLS_ROOT / _INTERNOS
        if not internos_root.exists():
            return encontrados
        for vertical_dir in sorted(internos_root.iterdir()):
            if not vertical_dir.is_dir() or not vertical_dir.name.startswith("vertical_"):
                continue
            if vertical_filter and vertical_dir.name != vertical_filter:
                continue
            for skill_dir in sorted(vertical_dir.iterdir()):
                if not skill_dir.is_dir() or skill_dir.name.startswith(("_", ".")):
                    continue
                if (skill_dir / "skill.py").exists():
                    encontrados.append((vertical_dir, skill_dir))
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
