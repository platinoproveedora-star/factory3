"""Detecta skills en carpeta sin registro, y entradas en registry sin carpeta."""
from __future__ import annotations

import json
from pathlib import Path

_SKILLS_ROOT = Path(__file__).parent.parent.parent  # factory/skills/
_FOLDERS     = ["internos", "meta", "eval"]


class SkillOrphanDetectorService:

    def ejecutar(self, context: dict) -> dict:
        if context.get("dry_run", False):
            return {"ok": True, "message": "dry_run", "data": context}

        registry = self._cargar_registry()
        en_disco  = self._escanear_disco()

        # En disco pero no en registry
        huerfanos = []
        for folder, name in en_disco:
            if name not in registry:
                huerfanos.append({"nombre": name, "folder": folder, "tipo": "huerfano",
                                   "descripcion": "carpeta existe, sin entrada en registry"})

        # En registry pero sin carpeta
        fantasmas = []
        disco_set = {name for _, name in en_disco}
        for name, entry in registry.items():
            path_rel = entry.get("path", "")
            # Determinar folder desde path
            folder = "internos"
            for f in _FOLDERS:
                if f"/{f}/" in path_rel or path_rel.startswith(f"skills/{f}/"):
                    folder = f
                    break
            skill_path = _SKILLS_ROOT / folder / name
            if not skill_path.exists():
                fantasmas.append({"nombre": name, "folder": folder, "tipo": "fantasma",
                                   "descripcion": "en registry pero sin carpeta en disco"})

        todos = huerfanos + fantasmas
        limpio = len(todos) == 0

        return {
            "ok": True,
            "message": "fabrica limpia" if limpio else f"{len(huerfanos)} huerfanos + {len(fantasmas)} fantasmas",
            "data": {
                "limpio":     limpio,
                "huerfanos":  len(huerfanos),
                "fantasmas":  len(fantasmas),
                "total_disco":    len(en_disco),
                "total_registry": len(registry),
                "problemas":  todos,
            },
        }

    def _escanear_disco(self) -> list[tuple[str, str]]:
        encontrados = []
        for folder in _FOLDERS:
            folder_path = _SKILLS_ROOT / folder
            if not folder_path.exists():
                continue
            for skill_dir in sorted(folder_path.iterdir()):
                if skill_dir.is_dir() and not skill_dir.name.startswith(("_", ".")):
                    encontrados.append((folder, skill_dir.name))
        return encontrados

    def _cargar_registry(self) -> dict:
        p = _SKILLS_ROOT / "registry.json"
        if not p.exists():
            return {}
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}
