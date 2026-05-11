"""Corre health_check + orphan_detector + manifest_validator + regression en una sola llamada."""
from __future__ import annotations

import importlib.util
import sys
import time
from pathlib import Path

_SKILLS_ROOT = Path(__file__).parent.parent.parent  # factory/skills/
_EVAL_ROOT   = str(_SKILLS_ROOT / "eval")


class SkillBatchEvalService:

    def ejecutar(self, context: dict) -> dict:
        if context.get("dry_run", False):
            return {"ok": True, "message": "dry_run", "data": context}

        resultados = {}
        errores    = 0
        t_total    = time.time()

        checks = [
            ("skill_health_check",       {"solo_problemas": False}),
            ("skill_orphan_detector",    {}),
            ("skill_manifest_validator", {}),
            ("regression_eval",          {}),
        ]

        for skill_name, ctx in checks:
            t0 = time.time()
            r  = self._run(skill_name, {**ctx, "dry_run": False})
            ms = int((time.time() - t0) * 1000)
            ok = r.get("ok", False)
            if not ok:
                errores += 1
            resultados[skill_name] = {
                "ok":      ok,
                "message": r.get("message", ""),
                "ms":      ms,
                "data":    r.get("data", {}),
                "error":   r.get("error"),
            }

        latencia_total = int((time.time() - t_total) * 1000)
        fabrica_ok     = errores == 0

        # Resumen ejecutivo
        hc   = resultados.get("skill_health_check", {}).get("data", {})
        orph = resultados.get("skill_orphan_detector", {}).get("data", {})
        mval = resultados.get("skill_manifest_validator", {}).get("data", {})
        regr = resultados.get("regression_eval", {}).get("data", {})

        resumen = {
            "fabrica_ok":           fabrica_ok,
            "skills_con_error":     hc.get("por_status", {}).get("error", 0),
            "skills_con_warning":   hc.get("por_status", {}).get("warning", 0),
            "skills_ok":            hc.get("por_status", {}).get("ok", 0),
            "huerfanos":            orph.get("huerfanos", 0),
            "fantasmas":            orph.get("fantasmas", 0),
            "manifests_invalidos":  mval.get("invalidos", 0),
            "regression_ok":        regr.get("ok", 0),
            "regression_total":     regr.get("total", 0),
            "latencia_total_ms":    latencia_total,
        }

        nivel = "FABRICA SANA" if fabrica_ok else f"ATENCION — {errores} checks con problemas"

        return {
            "ok":      fabrica_ok,
            "message": nivel,
            "data": {
                "resumen":     resumen,
                "resultados":  resultados,
            },
        }

    def _run(self, skill_name: str, ctx: dict) -> dict:
        skill_path = Path(_EVAL_ROOT) / skill_name
        entrypoint = skill_path / "skill.py"
        if not entrypoint.exists():
            return {"ok": False, "error": f"skill no encontrado: {skill_name}"}
        module_name = f"_batch_{skill_name}"
        spec = importlib.util.spec_from_file_location(module_name, entrypoint)
        if not spec or not spec.loader:
            return {"ok": False, "error": f"error cargando: {skill_name}"}
        module = importlib.util.module_from_spec(spec)
        sys.path.insert(0, str(skill_path))
        try:
            spec.loader.exec_module(module)
            return module.run(ctx)
        except Exception as e:
            return {"ok": False, "error": str(e)}
        finally:
            if sys.path and sys.path[0] == str(skill_path):
                sys.path.pop(0)
