"""Ejecuta un skill con input de prueba y evalúa la calidad del output."""
from __future__ import annotations

import importlib.util
import sys
import time
from pathlib import Path


_SKILLS_ROOT = Path(__file__).parent.parent.parent   # factory/skills/


class SkillQualityEvalService:

    def ejecutar(self, context: dict) -> dict:
        skill_name = (context.get("skill_name") or "").strip()
        test_input  = context.get("test_input") or {}
        source      = (context.get("source") or "internos").strip()

        if not skill_name:
            return {"ok": False, "error": "skill_name requerido"}

        if context.get("dry_run", False):
            return {"ok": True, "message": "dry_run", "data": context}

        skill_path = self._resolve_skill_path(skill_name, source)
        if not skill_path:
            return {"ok": False, "error": f"skill no encontrado: {skill_name} (source={source})"}

        skill_module = self._load_skill(skill_path, skill_name)
        if skill_module is None:
            return {"ok": False, "error": f"error cargando skill: {skill_name}"}

        run_input = {**test_input, "dry_run": False}
        t0 = time.time()
        try:
            result = skill_module.run(run_input)
        except Exception as e:
            return {"ok": False, "error": f"excepción en skill.run: {e}"}
        latencia_ms = int((time.time() - t0) * 1000)

        checks = self._evaluar(result, latencia_ms)
        score  = sum(1 for c in checks if c["pass"]) / max(len(checks), 1)

        return {
            "ok": True,
            "message": f"score {score:.0%} — {sum(1 for c in checks if c['pass'])}/{len(checks)} checks",
            "data": {
                "skill_name": skill_name,
                "score": round(score, 2),
                "latencia_ms": latencia_ms,
                "checks": checks,
                "raw_output": result,
            },
        }

    def _evaluar(self, result: dict, latencia_ms: int) -> list:
        checks = []

        checks.append({"check": "retorna dict", "pass": isinstance(result, dict)})

        if isinstance(result, dict):
            checks.append({"check": "tiene ok", "pass": "ok" in result})
            checks.append({"check": "ok es bool", "pass": isinstance(result.get("ok"), bool)})
            checks.append({"check": "ok=True", "pass": result.get("ok") is True})
            checks.append({"check": "tiene data o message", "pass": "data" in result or "message" in result})
            if not result.get("ok"):
                checks.append({"check": "error tiene mensaje", "pass": bool(result.get("error"))})

        checks.append({"check": "latencia < 10s", "pass": latencia_ms < 10_000})
        checks.append({"check": "latencia < 30s", "pass": latencia_ms < 30_000})

        return checks

    def _resolve_skill_path(self, name: str, source: str) -> Path | None:
        roots = {
            "internos": _SKILLS_ROOT / "internos",
            "meta":     _SKILLS_ROOT / "meta",
            "eval":     _SKILLS_ROOT / "eval",
        }
        root = roots.get(source)
        if root is None:
            # absolute path fallback
            candidate = Path(source) / name
            if (candidate / "skill.py").exists():
                return candidate
            return None
        candidate = root / name
        if (candidate / "skill.py").exists():
            return candidate
        return None

    def _load_skill(self, skill_path: Path, skill_name: str):
        entrypoint = skill_path / "skill.py"
        module_name = f"_quality_eval_{skill_name}"
        spec = importlib.util.spec_from_file_location(module_name, entrypoint)
        if not spec or not spec.loader:
            return None
        module = importlib.util.module_from_spec(spec)
        sys.path.insert(0, str(skill_path))
        try:
            spec.loader.exec_module(module)
        except Exception:
            return None
        finally:
            if sys.path and sys.path[0] == str(skill_path):
                sys.path.pop(0)
        return module
