"""Corre skills existentes con dry_run=True y verifica que retornen ok:true."""
from __future__ import annotations

import importlib.util
import sys
import time
from pathlib import Path


_FACTORY_ROOT = Path(__file__).parent.parent.parent.parent

_DEFAULT_SKILLS = [
    ("rh_basic_validation",   "internos", {"candidato_id": "test-dry"}),
    ("rh_candidate_scoring",  "internos", {"candidato_id": "test-dry", "vacante_id": "test-dry"}),
    ("rh_candidate_ranking",  "internos", {"vacante_id": "test-dry"}),
    ("rh_candidate_search",   "internos", {"query": "test"}),
    ("meta_task_enqueue",     "meta",     {"skill": "test_skill", "context": {}}),
    ("meta_task_status",      "meta",     {"folio": "TASK-0001"}),
    ("workflow_capture",      "meta",     {"proceso": "test proceso"}),
    ("pattern_extractor",     "meta",     {"pasos": [{"numero": 1, "accion": "test"}]}),
]


class RegressionEvalService:

    def ejecutar(self, context: dict) -> dict:
        skills_override = context.get("skills")
        if skills_override:
            skills_to_test = [(s["name"], s.get("source", "internos"), s.get("input", {})) for s in skills_override]
        else:
            skills_to_test = _DEFAULT_SKILLS

        if context.get("dry_run", False):
            return {"ok": True, "message": "dry_run", "data": {"skills_a_probar": len(skills_to_test)}}

        resultados = []
        errores = 0
        for skill_name, source, test_input in skills_to_test:
            r = self._run_one(skill_name, source, test_input)
            resultados.append(r)
            if not r["pass"]:
                errores += 1

        return {
            "ok": errores == 0,
            "message": f"{len(resultados) - errores}/{len(resultados)} skills OK",
            "data": {
                "total": len(resultados),
                "ok": len(resultados) - errores,
                "errores": errores,
                "resultados": resultados,
            },
        }

    def _run_one(self, skill_name: str, source: str, test_input: dict) -> dict:
        skill_path = self._resolve(skill_name, source)
        if not skill_path:
            return {"skill": skill_name, "pass": False, "error": "no encontrado", "latencia_ms": 0}

        module = self._load(skill_path, skill_name)
        if module is None:
            return {"skill": skill_name, "pass": False, "error": "error al cargar", "latencia_ms": 0}

        run_input = {**test_input, "dry_run": True}
        t0 = time.time()
        try:
            result = module.run(run_input)
        except Exception as e:
            return {"skill": skill_name, "pass": False, "error": str(e), "latencia_ms": int((time.time() - t0) * 1000)}
        latencia_ms = int((time.time() - t0) * 1000)

        passed = isinstance(result, dict) and result.get("ok") is True
        return {
            "skill": skill_name,
            "pass": passed,
            "ok": result.get("ok") if isinstance(result, dict) else None,
            "error": result.get("error") if isinstance(result, dict) and not passed else None,
            "latencia_ms": latencia_ms,
        }

    def _resolve(self, name: str, source: str) -> Path | None:
        roots = {
            "internos": _FACTORY_ROOT / "internos",
            "meta":     _FACTORY_ROOT / "meta",
            "eval":     _FACTORY_ROOT / "eval",
        }
        root = roots.get(source)
        if root is None:
            candidate = Path(source) / name
            if (candidate / "skill.py").exists():
                return candidate
            return None
        candidate = root / name
        if (candidate / "skill.py").exists():
            return candidate
        return None

    def _load(self, skill_path: Path, skill_name: str):
        entrypoint = skill_path / "skill.py"
        module_name = f"_regression_{skill_name}"
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
