"""KPIs de meta y eval skills: conteo, cobertura, salud y registro."""
from __future__ import annotations

import json
from pathlib import Path

_SKILLS_ROOT = Path(__file__).parent.parent.parent  # factory/skills/
_FOLDERS     = ["meta", "eval"]
_REQUIRED    = ["manifest.json", "skill.py", "service.py"]

_PIPELINE_META = [
    "workflow_capture", "pattern_extractor", "skill_spec_generator",
    "skill_code_generator", "skill_cases_generator", "skill_doc_generator",
    "skill_registry_sync", "proceso_to_skill",
]
_PIPELINE_EVAL = [
    "skill_health_check", "skill_orphan_detector", "skill_manifest_validator",
    "skill_safety_eval", "skill_quality_eval", "skill_breaking_detector",
    "regression_eval", "skill_batch_eval", "skill_import_checker",
    "factory_stats", "meta_eval_kpis",
]


class MetaEvalKpisService:

    def ejecutar(self, context: dict) -> dict:
        if context.get("dry_run", False):
            return {"ok": True, "message": "dry_run", "data": context}

        registry = self._cargar_registry()
        meta_skills = self._escanear("meta", registry)
        eval_skills = self._escanear("eval", registry)

        meta_kpis = self._calcular_kpis(meta_skills, _PIPELINE_META)
        eval_kpis = self._calcular_kpis(eval_skills, _PIPELINE_EVAL)

        pipeline_meta_ok = [s for s in _PIPELINE_META if any(x["nombre"] == s and x["completo"] for x in meta_skills)]
        pipeline_eval_ok = [s for s in _PIPELINE_EVAL if any(x["nombre"] == s and x["completo"] for x in eval_skills)]

        cobertura_pipeline = round(
            (len(pipeline_meta_ok) + len(pipeline_eval_ok)) /
            max(len(_PIPELINE_META) + len(_PIPELINE_EVAL), 1) * 100
        )

        return {
            "ok": True,
            "message": (
                f"{meta_kpis['total']} meta · {eval_kpis['total']} eval · "
                f"pipeline {cobertura_pipeline}% cubierto"
            ),
            "data": {
                "resumen": {
                    "total_meta":          meta_kpis["total"],
                    "total_eval":          eval_kpis["total"],
                    "meta_completos":      meta_kpis["completos"],
                    "eval_completos":      eval_kpis["completos"],
                    "meta_en_registry":    meta_kpis["en_registry"],
                    "eval_en_registry":    eval_kpis["en_registry"],
                    "cobertura_pipeline":  cobertura_pipeline,
                    "pipeline_meta_ok":    len(pipeline_meta_ok),
                    "pipeline_eval_ok":    len(pipeline_eval_ok),
                },
                "pipeline": {
                    "meta": [
                        {
                            "nombre": s,
                            "estado": "ok" if s in pipeline_meta_ok else "falta",
                            "semaforo": "🟢" if s in pipeline_meta_ok else "🔴",
                        }
                        for s in _PIPELINE_META
                    ],
                    "eval": [
                        {
                            "nombre": s,
                            "estado": "ok" if s in pipeline_eval_ok else "falta",
                            "semaforo": "🟢" if s in pipeline_eval_ok else "🔴",
                        }
                        for s in _PIPELINE_EVAL
                    ],
                },
                "meta_skills": meta_skills,
                "eval_skills": eval_skills,
            },
        }

    def _escanear(self, folder: str, registry: dict) -> list:
        skills = []
        p = _SKILLS_ROOT / folder
        if not p.exists():
            return skills
        for skill_dir in sorted(p.iterdir()):
            if not skill_dir.is_dir() or skill_dir.name.startswith(("_", ".")):
                continue
            name     = skill_dir.name
            archivos = {f: (skill_dir / f).exists() for f in _REQUIRED}
            completo = all(archivos.values())
            manifest = self._leer_manifest(skill_dir)
            skills.append({
                "nombre":      name,
                "folder":      folder,
                "completo":    completo,
                "en_registry": name in registry,
                "semaforo":    "🟢" if completo and name in registry else ("🟡" if completo else "🔴"),
                "archivos":    archivos,
                "descripcion": manifest.get("description", ""),
                "kind":        manifest.get("kind", "executable"),
            })
        return skills

    def _calcular_kpis(self, skills: list, pipeline: list) -> dict:
        return {
            "total":      len(skills),
            "completos":  sum(1 for s in skills if s["completo"]),
            "en_registry":sum(1 for s in skills if s["en_registry"]),
            "incompletos":sum(1 for s in skills if not s["completo"]),
        }

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
