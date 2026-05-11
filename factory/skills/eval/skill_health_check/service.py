"""Escanea todos los skills y reporta su estado de salud."""
from __future__ import annotations

import json
from pathlib import Path

_SKILLS_ROOT = Path(__file__).parent.parent.parent  # factory/skills/
_REQUIRED_FILES   = ["manifest.json", "skill.py", "service.py"]
_REQUIRED_FIELDS  = ["name", "type", "kind", "entrypoint", "description"]
_FOLDERS          = ["internos", "meta", "eval"]
_SEMAFORO         = {"ok": "🟢", "warning": "🟡", "error": "🔴"}


class SkillHealthCheckService:

    def ejecutar(self, context: dict) -> dict:
        folders  = context.get("folders") or _FOLDERS
        solo_mal = context.get("solo_problemas", False)

        if context.get("dry_run", False):
            return {"ok": True, "message": "dry_run", "data": context}

        registry = self._cargar_registry()
        resultados = []

        for folder in folders:
            folder_path = _SKILLS_ROOT / folder
            if not folder_path.exists():
                continue
            for skill_dir in sorted(folder_path.iterdir()):
                if not skill_dir.is_dir() or skill_dir.name.startswith(("_", ".")):
                    continue
                r = self._revisar(skill_dir, folder, registry)
                if not solo_mal or r["status"] != "ok":
                    resultados.append(r)

        por_status = {"ok": 0, "warning": 0, "error": 0}
        for r in resultados:
            por_status[r["status"]] = por_status.get(r["status"], 0) + 1

        return {
            "ok": True,
            "message": (
                f"{_SEMAFORO['ok']} {por_status['ok']} OK  "
                f"{_SEMAFORO['warning']} {por_status['warning']} warnings  "
                f"{_SEMAFORO['error']} {por_status['error']} errores"
            ),
            "data": {
                "total":    len(resultados),
                "por_status": por_status,
                "skills":   resultados,
            },
        }

    def _revisar(self, skill_dir: Path, folder: str, registry: dict) -> dict:
        name   = skill_dir.name
        issues = []

        for f in _REQUIRED_FILES:
            if not (skill_dir / f).exists():
                issues.append(f"falta {f}")

        if name not in registry:
            issues.append("no está en registry.json")

        manifest_path = skill_dir / "manifest.json"
        if manifest_path.exists():
            try:
                m = json.loads(manifest_path.read_text(encoding="utf-8"))
                for field in _REQUIRED_FIELDS:
                    if not m.get(field):
                        issues.append(f"manifest sin campo '{field}'")
            except Exception:
                issues.append("manifest.json inválido (JSON roto)")

        if not issues:
            status = "ok"
        elif len(issues) == 1 and "registry" in issues[0]:
            status = "warning"
        else:
            status = "error"

        return {
            "nombre":      name,
            "folder":      folder,
            "status":      status,
            "semaforo":    _SEMAFORO.get(status, "⚫"),
            "issues":      issues,
            "en_registry": name in registry,
            "service_py":  (skill_dir / "service.py").exists(),
            "skill_py":    (skill_dir / "skill.py").exists(),
            "manifest":    (skill_dir / "manifest.json").exists(),
        }

    def _cargar_registry(self) -> dict:
        p = _SKILLS_ROOT / "registry.json"
        if not p.exists():
            return {}
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}
