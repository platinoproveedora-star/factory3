from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any


class FactoryModulePublishCheckService:
    def ejecutar(self, context: dict) -> dict:
        repo_root = Path(__file__).resolve().parents[5]
        project_path_result = self._resolve_project_path(repo_root, context)
        if not project_path_result.get("ok"):
            return project_path_result

        project_path = project_path_result["path"]
        project_json = self._read_json(project_path / "project.json")
        if project_json is None:
            return {"ok": False, "error": "project.json requerido"}

        module_code = str(context.get("module_code") or project_json.get("module_code") or "").strip()
        schema = str(context.get("schema") or project_json.get("schema") or "").strip()
        company_id = str(context.get("company_id") or context.get("empresa_id") or project_json.get("company_id") or "").strip()
        project_code = str(context.get("project_code") or project_json.get("project_code") or "").strip()
        vertical = str(context.get("vertical") or "").strip()

        checks = []
        checks.append(self._check("project_json", bool(company_id and project_code and module_code and schema), "project.json tiene company_id, project_code, module_code y schema"))
        checks.append(self._check("env_example", (project_path / ".env.example").exists(), ".env.example existe"))
        checks.append(self._check("package_json", (project_path / "package.json").exists(), "dashboard/package.json existe", severity="warning"))

        registry = self._read_json(repo_root / "factory" / "skills" / "registry.json") or {}
        registry_matches = self._registry_matches(registry, module_code, vertical)
        checks.append(self._check("registry", bool(registry_matches), "hay skills registrados para el modulo o vertical"))

        skill_results = self._skill_file_checks(repo_root, registry_matches)
        checks.extend(skill_results["checks"])

        marketplace_expected = bool(context.get("require_marketplace", True))
        if marketplace_expected:
            marketable = self._marketplace_entry_exists(registry, module_code)
            checks.append(self._check("marketplace_skill", marketable, "existen skills de marketplace para registrar/listar/activar modulos"))

        dashboard_path = Path(str(context.get("dashboard_path") or project_path))
        if not dashboard_path.is_absolute():
            dashboard_path = repo_root / dashboard_path
        dashboard_checks = self._dashboard_checks(dashboard_path)
        checks.extend(dashboard_checks)

        audit_paths = context.get("paths") or [self._rel(project_path, repo_root)]
        if vertical:
            audit_paths.append(f"factory/skills/internos/{vertical}")
        audit_result = self._run_hardcode_audit(repo_root, audit_paths)
        checks.append(self._check("no_hardcode_audit", audit_result.get("ok", False), "factory_no_hardcode_audit sin blockers"))

        blockers = [item for item in checks if item["status"] == "fail" and item["severity"] == "blocker"]
        warnings = [item for item in checks if item["status"] == "fail" and item["severity"] == "warning"]
        ready = not blockers
        return {
            "ok": ready,
            "data": {
                "ready": ready,
                "company_id": company_id,
                "project_code": project_code,
                "module_code": module_code,
                "schema": schema,
                "project_path": self._rel(project_path, repo_root),
                "summary": {"blockers": len(blockers), "warnings": len(warnings), "checks": len(checks)},
                "checks": checks,
                "registry_matches": registry_matches,
                "hardcode_audit": audit_result.get("data") or audit_result,
                "next_actions": self._next_actions(blockers, warnings),
            },
            "error": f"{len(blockers)} blockers de publicacion" if blockers else None,
        }

    def _resolve_project_path(self, repo_root: Path, context: dict) -> dict:
        raw = str(context.get("project_path") or "").strip()
        if raw:
            path = Path(raw)
            if not path.is_absolute():
                path = repo_root / path
            if not path.exists():
                return {"ok": False, "error": "project_path no existe"}
            return {"ok": True, "path": path}

        company_id = str(context.get("company_id") or context.get("empresa_id") or "").strip()
        project_code = str(context.get("project_code") or "").strip()
        if not company_id or not project_code:
            return {"ok": False, "error": "project_path o company_id/project_code requerido"}
        base = repo_root / "companies" / company_id / "projects"
        matches = sorted(path for path in base.glob(f"{project_code}*") if path.is_dir())
        if not matches:
            return {"ok": False, "error": "no se encontro proyecto para company_id/project_code"}
        return {"ok": True, "path": matches[0]}

    def _check(self, name: str, passed: bool, message: str, severity: str = "blocker") -> dict:
        return {"name": name, "status": "pass" if passed else "fail", "severity": severity, "message": message}

    def _registry_matches(self, registry: dict[str, Any], module_code: str, vertical: str) -> list[str]:
        matches = []
        for name, meta in registry.items():
            meta_vertical = str(meta.get("vertical") or "")
            text = f"{name} {meta.get('descripcion', '')} {meta.get('path', '')}"
            if vertical and meta_vertical == vertical:
                matches.append(name)
            elif module_code and module_code in text:
                matches.append(name)
        return sorted(set(matches))

    def _skill_file_checks(self, repo_root: Path, skill_names: list[str]) -> dict:
        registry = self._read_json(repo_root / "factory" / "skills" / "registry.json") or {}
        checks = []
        for skill_name in skill_names:
            meta = registry.get(skill_name) or {}
            path = repo_root / "factory" / str(meta.get("path") or "")
            checks.append(self._check(f"{skill_name}:manifest", (path / "manifest.json").exists(), "skill tiene manifest.json"))
            checks.append(self._check(f"{skill_name}:skill", (path / "skill.py").exists(), "skill tiene skill.py"))
            checks.append(self._check(f"{skill_name}:service", (path / "service.py").exists(), "skill tiene service.py"))
        return {"checks": checks}

    def _marketplace_entry_exists(self, registry: dict[str, Any], module_code: str) -> bool:
        needed = {
            "vertical_apps4all_marketplace/apps4all_marketplace_module_register",
            "vertical_apps4all_marketplace/apps4all_marketplace_module_list",
            "vertical_apps4all_marketplace/apps4all_marketplace_module_activate",
        }
        return needed.issubset(set(registry.keys())) and bool(module_code)

    def _dashboard_checks(self, dashboard_path: Path) -> list[dict]:
        checks = []
        if not dashboard_path.exists():
            return [self._check("dashboard_path", False, "dashboard_path existe", severity="warning")]
        expected = ["project.json", "package.json", "lib/auth.ts", "lib/platform.ts"]
        for rel in expected:
            checks.append(self._check(f"dashboard:{rel}", (dashboard_path / rel).exists(), f"{rel} existe", severity="warning"))
        return checks

    def _run_hardcode_audit(self, repo_root: Path, paths: list[str]) -> dict:
        service_file = repo_root / "factory" / "skills" / "internos" / "vertical_factory_utils" / "factory_no_hardcode_audit" / "service.py"
        if not service_file.exists():
            return {"ok": False, "error": "factory_no_hardcode_audit no encontrado"}
        spec = importlib.util.spec_from_file_location("_factory_no_hardcode_audit_service", service_file)
        if spec is None or spec.loader is None:
            return {"ok": False, "error": "no se pudo cargar factory_no_hardcode_audit"}
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.FactoryNoHardcodeAuditService().ejecutar({"paths": paths})

    def _next_actions(self, blockers: list[dict], warnings: list[dict]) -> list[str]:
        actions = []
        if blockers:
            actions.append("corregir blockers antes de vender o clonar")
        if warnings:
            actions.append("revisar warnings y documentar si son config/env permitidos")
        if not blockers:
            actions.append("registrar modulo en marketplace y crear demo seed real")
            actions.append("correr build/smoke del dashboard antes de deploy")
        return actions

    def _read_json(self, path: Path) -> dict | None:
        try:
            return json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            return None

    def _rel(self, path: Path, repo_root: Path) -> str:
        try:
            return str(path.relative_to(repo_root)).replace("\\", "/")
        except ValueError:
            return str(path)
