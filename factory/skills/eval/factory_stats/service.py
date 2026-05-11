"""KPIs globales de la fábrica: skills, bots y agents."""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

_FACTORY_ROOT = Path(__file__).parent.parent.parent.parent  # factory/
_SKILLS_ROOT  = _FACTORY_ROOT / "skills"
_FOLDERS      = ["internos", "meta", "eval"]


class FactoryStatsService:

    def ejecutar(self, context: dict) -> dict:
        if context.get("dry_run", False):
            return {"ok": True, "message": "dry_run", "data": context}

        registry  = self._cargar_json(_SKILLS_ROOT / "registry.json")
        bots      = self._cargar_json(_FACTORY_ROOT / "bots" / "registry.json")
        agents    = self._cargar_json(_FACTORY_ROOT / "agents" / "registry.json")

        # --- por tipo ---
        por_tipo: dict[str, int] = defaultdict(int)
        por_vertical: dict[str, int] = defaultdict(int)
        por_kind: dict[str, int] = defaultdict(int)
        data_skills = []

        for name, entry in registry.items():
            t = entry.get("tipo", "interno")
            v = entry.get("vertical", "sin_vertical")
            k = entry.get("kind", "executable")
            por_tipo[t]      += 1
            por_vertical[v]  += 1
            por_kind[k]      += 1
            if k == "data":
                data_skills.append(name)

        # --- en disco ---
        en_disco: dict[str, int] = {}
        for folder in _FOLDERS:
            p = _SKILLS_ROOT / folder
            en_disco[folder] = sum(1 for d in p.iterdir() if d.is_dir() and not d.name.startswith("_")) if p.exists() else 0

        total_disco    = sum(en_disco.values())
        total_registry = len(registry)
        sincronizado   = total_disco == total_registry

        return {
            "ok": True,
            "message": f"{total_registry} skills · {len(bots)} bots · {len(agents)} agents",
            "data": {
                "skills": {
                    "total":          total_registry,
                    "en_disco":       total_disco,
                    "sincronizado":   sincronizado,
                    "por_tipo":       dict(por_tipo),
                    "por_kind":       dict(por_kind),
                    "data_endpoints": data_skills,
                    "por_folder":     en_disco,
                    "top_verticales": dict(sorted(por_vertical.items(), key=lambda x: -x[1])[:10]),
                },
                "bots":   {"total": len(bots),   "nombres": list(bots.keys())},
                "agents": {"total": len(agents),  "nombres": list(agents.keys())},
            },
        }

    def _cargar_json(self, path: Path) -> dict:
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}
