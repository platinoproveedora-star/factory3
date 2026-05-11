"""Orquestador: texto de proceso → skill completo (spec → código → eval → registro → push)."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_SKILLS_ROOT = Path(__file__).parent.parent.parent   # factory/skills/
_META_ROOT   = str(_SKILLS_ROOT / "meta")
_EVAL_ROOT   = str(_SKILLS_ROOT / "eval")
_INT_ROOT    = str(_SKILLS_ROOT / "internos")


class ProcesoToSkillService:

    def ejecutar(self, context: dict) -> dict:
        proceso   = (context.get("proceso") or "").strip()
        vertical  = (context.get("vertical") or "general").strip()
        patron_ix = int(context.get("patron_index", 0))
        push      = context.get("push", False)
        dry_run   = context.get("dry_run", False)

        if not proceso:
            return {"ok": False, "error": "proceso requerido — describe el proceso en texto"}

        pasos_result = []
        log = []

        # 1. Capturar proceso
        r1 = self._run(_META_ROOT, "workflow_capture", {"proceso": proceso, "dry_run": dry_run})
        log.append({"paso": "workflow_capture", "ok": r1.get("ok"), "message": r1.get("message", "")})
        if not r1.get("ok"):
            return {"ok": False, "error": f"workflow_capture falló: {r1.get('error')}", "data": {"log": log}}
        pasos = r1["data"].get("pasos", [])
        nombre_sugerido = r1["data"].get("nombre_sugerido", "nuevo_skill")

        # 2. Extraer patrones
        r2 = self._run(_META_ROOT, "pattern_extractor", {
            "pasos": pasos, "proceso_nombre": nombre_sugerido, "dry_run": dry_run
        })
        log.append({"paso": "pattern_extractor", "ok": r2.get("ok"), "message": r2.get("message", "")})
        if not r2.get("ok"):
            return {"ok": False, "error": f"pattern_extractor falló: {r2.get('error')}", "data": {"log": log}}

        patrones = r2["data"].get("patrones", [])
        automatizables = [p for p in patrones if p.get("automatizable")]
        if not automatizables:
            return {"ok": False, "error": "no se encontraron patrones automatizables en el proceso", "data": {"log": log, "patrones": patrones}}

        patron = automatizables[patron_ix] if patron_ix < len(automatizables) else automatizables[0]

        # 3. Generar spec
        r3 = self._run(_META_ROOT, "skill_spec_generator", {
            "patron": patron, "proceso_contexto": proceso, "dry_run": dry_run
        })
        log.append({"paso": "skill_spec_generator", "ok": r3.get("ok"), "message": r3.get("message", "")})
        if not r3.get("ok"):
            return {"ok": False, "error": f"skill_spec_generator falló: {r3.get('error')}", "data": {"log": log}}

        spec = r3["data"]
        if vertical != "general":
            spec["vertical"] = vertical

        if dry_run:
            return {
                "ok": True,
                "message": f"dry_run — spec lista: {spec.get('skill_name', '?')}",
                "data": {"log": log, "spec": spec, "patron": patron},
            }

        # 4. Generar código
        r4 = self._run(_META_ROOT, "skill_code_generator", {"spec": spec, "dry_run": False})
        log.append({"paso": "skill_code_generator", "ok": r4.get("ok"), "message": r4.get("message", "")})
        if not r4.get("ok"):
            return {"ok": False, "error": f"skill_code_generator falló: {r4.get('error')}", "data": {"log": log}}

        codigo = r4["data"]

        # 5. Generar casos de prueba
        r5 = self._run(_META_ROOT, "skill_cases_generator", {"spec": spec, "n_casos": 5, "dry_run": False})
        log.append({"paso": "skill_cases_generator", "ok": r5.get("ok"), "message": r5.get("message", "")})
        casos = r5.get("data", {}).get("casos", []) if r5.get("ok") else []

        # 6. Crear archivos via new_skill (service_py_override inyecta código generado)
        skill_name = spec["skill_name"]
        _factory_base = str(_SKILLS_ROOT.parent)   # factory/
        r6 = self._run(_INT_ROOT, "new_skill", {
            "nombre":             skill_name,
            "vertical":           spec.get("vertical", vertical),
            "descripcion":        spec.get("descripcion", ""),
            "dry_run":            False,
            "base_dir":           _factory_base,
            "service_py_override": codigo["service_py"],
        })
        log.append({"paso": "new_skill", "ok": r6.get("ok"), "message": r6.get("message", "")})
        if not r6.get("ok"):
            return {"ok": False, "error": f"new_skill falló: {r6.get('error')}", "data": {"log": log, "codigo": codigo}}

        # 7. Safety eval sobre el skill recién creado en disco
        r7 = self._run(_EVAL_ROOT, "skill_safety_eval", {
            "skill_name": skill_name,
            "source":     "internos",
            "dry_run":    False,
        })
        log.append({"paso": "skill_safety_eval", "ok": r7.get("ok"), "message": r7.get("message", "")})

        # 8. Push a GitHub (opcional)
        push_result = None
        if push:
            import os
            repo   = os.getenv("GITHUB_REPO", "")
            branch = os.getenv("GITHUB_BRANCH", "main")
            r8 = self._run(_INT_ROOT, "github_push", {
                "repo": repo, "branch": branch,
                "message": f"feat: add auto-generated skill {skill_name}",
                "files": {
                    f"factory/skills/internos/{skill_name}/service.py": codigo["service_py"],
                    f"factory/skills/internos/{skill_name}/skill.py":   codigo["skill_py"],
                    f"factory/skills/internos/{skill_name}/manifest.json": codigo.get("manifest_json", {}),
                },
                "dry_run": False,
            })
            log.append({"paso": "github_push", "ok": r8.get("ok"), "message": r8.get("message", "")})
            push_result = r8

        return {
            "ok": True,
            "message": f"skill '{skill_name}' creado — {len(log)} pasos completados",
            "data": {
                "skill_name":   skill_name,
                "spec":         spec,
                "codigo":       codigo,
                "casos_prueba": casos,
                "safety":       r7.get("data", {}),
                "log":          log,
                "push":         push_result,
            },
        }

    def _run(self, source_root: str, skill_name: str, ctx: dict) -> dict:
        skill_path = Path(source_root) / skill_name
        entrypoint = skill_path / "skill.py"
        if not entrypoint.exists():
            return {"ok": False, "error": f"skill no encontrado: {skill_name} en {source_root}"}
        module_name = f"_pts_{skill_name}"
        spec = importlib.util.spec_from_file_location(module_name, entrypoint)
        if not spec or not spec.loader:
            return {"ok": False, "error": f"error cargando spec: {skill_name}"}
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
