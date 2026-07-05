from __future__ import annotations

import json
from pathlib import Path


class FactoryModuleClonePlanService:
    def ejecutar(self, context: dict) -> dict:
        repo_root = Path(__file__).resolve().parents[5]
        source_path = self._resolve_source(repo_root, context)
        if not source_path.get("ok"):
            return source_path

        project_path = source_path["path"]
        project_json = self._read_json(project_path / "project.json")
        if project_json is None:
            return {"ok": False, "error": "source project.json requerido"}

        target_company_id = str(context.get("target_company_id") or context.get("target_empresa_id") or "").strip().upper()
        target_project_code = str(context.get("target_project_code") or "").strip()
        target_module_code = str(context.get("target_module_code") or project_json.get("module_code") or "").strip()
        target_schema = str(context.get("target_schema") or "").strip()
        if not target_company_id or not target_project_code or not target_module_code or not target_schema:
            return {"ok": False, "error": "target_company_id, target_project_code, target_module_code y target_schema requeridos"}

        source_company_id = str(project_json.get("company_id") or "")
        source_project_code = str(project_json.get("project_code") or "")
        source_module_code = str(project_json.get("module_code") or "")
        source_schema = str(project_json.get("schema") or "")

        target_path = Path(str(context.get("target_path") or Path("companies") / target_company_id / "projects" / f"{target_project_code}_{target_module_code.upper()}"))
        if target_path.is_absolute():
            rel_target_path = self._rel(target_path, repo_root)
        else:
            rel_target_path = str(target_path).replace("\\", "/")

        replacements = {
            source_company_id: target_company_id,
            source_project_code: target_project_code,
            source_module_code: target_module_code,
            source_schema: target_schema,
        }
        replacements = {key: value for key, value in replacements.items() if key and value and key != value}

        files = self._files_to_clone(project_path, repo_root)
        plan = {
            "source_project_path": self._rel(project_path, repo_root),
            "target_project_path": rel_target_path,
            "target_project_json": {
                **project_json,
                "company_id": target_company_id,
                "project_code": target_project_code,
                "module_code": target_module_code,
                "schema": target_schema,
            },
            "copy_files": files,
            "replace_tokens": replacements,
            "skip_dirs": ["node_modules", ".next", ".git", "__pycache__", "dist", "build"],
            "post_clone_steps": [
                "crear o validar companies/<EMPRESA>/company.json",
                "aplicar schema SQL del modulo con dry_run=false autorizado",
                "registrar modulo en marketplace",
                "crear demo seed para empresa destino",
                "correr factory_module_publish_check",
                "correr build/smoke del dashboard si aplica",
            ],
        }
        return {"ok": True, "data": plan}

    def _resolve_source(self, repo_root: Path, context: dict) -> dict:
        raw = str(context.get("source_project_path") or context.get("project_path") or "").strip()
        if raw:
            path = Path(raw)
            if not path.is_absolute():
                path = repo_root / path
            if not path.exists():
                return {"ok": False, "error": "source_project_path no existe"}
            return {"ok": True, "path": path}
        company_id = str(context.get("source_company_id") or context.get("company_id") or context.get("empresa_id") or "").strip()
        project_code = str(context.get("source_project_code") or context.get("project_code") or "").strip()
        if not company_id or not project_code:
            return {"ok": False, "error": "source_project_path o source_company_id/source_project_code requerido"}
        base = repo_root / "companies" / company_id / "projects"
        matches = sorted(path for path in base.glob(f"{project_code}*") if path.is_dir())
        if not matches:
            return {"ok": False, "error": "no se encontro proyecto fuente"}
        return {"ok": True, "path": matches[0]}

    def _files_to_clone(self, project_path: Path, repo_root: Path) -> list[str]:
        skip = {"node_modules", ".next", ".git", "__pycache__", "dist", "build"}
        files = []
        for path in project_path.rglob("*"):
            if not path.is_file() or any(part in skip for part in path.parts):
                continue
            files.append(self._rel(path, repo_root))
        return sorted(files)

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
