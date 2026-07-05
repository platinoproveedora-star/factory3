from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path


class Apps4AllModuleCloneExecuteService:
    def ejecutar(self, context: dict) -> dict:
        repo_root = Path(__file__).resolve().parents[5]
        plan_result = self._plan(repo_root, context)
        if not plan_result.get("ok"):
            return plan_result
        plan = plan_result.get("data") or {}
        target_path = repo_root / str(plan.get("target_project_path") or "")
        source_path = repo_root / str(plan.get("source_project_path") or "")
        guard = self._guard(repo_root, source_path, target_path)
        if not guard.get("ok"):
            return guard

        files = plan.get("copy_files") or []
        preview = {
            "source_project_path": plan.get("source_project_path"),
            "target_project_path": plan.get("target_project_path"),
            "files": len(files),
            "replace_tokens": plan.get("replace_tokens") or {},
            "overwrite": bool(context.get("overwrite", False)),
        }
        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run", "data": preview}
        if context.get("confirm_clone") is not True:
            return {"ok": False, "error": "confirm_clone=true requerido para escribir"}

        overwrite = bool(context.get("overwrite", False))
        replacements = plan.get("replace_tokens") or {}
        written = []
        skipped = []
        for rel in files:
            src = repo_root / rel
            if not src.exists() or not src.is_file():
                skipped.append(rel)
                continue
            local_rel = src.relative_to(source_path)
            dst = target_path / local_rel
            if dst.exists() and not overwrite:
                skipped.append(str(dst.relative_to(repo_root)).replace("\\", "/"))
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            if self._is_text(src):
                text = src.read_text(encoding="utf-8-sig", errors="ignore")
                dst.write_text(self._replace(text, replacements), encoding="utf-8")
            else:
                shutil.copy2(src, dst)
            written.append(str(dst.relative_to(repo_root)).replace("\\", "/"))

        project_json = plan.get("target_project_json") or {}
        if project_json:
            path = target_path / "project.json"
            path.write_text(json.dumps(project_json, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            if str(path.relative_to(repo_root)).replace("\\", "/") not in written:
                written.append(str(path.relative_to(repo_root)).replace("\\", "/"))

        return {"ok": True, "message": "clone complete", "data": {"written": written, "skipped": skipped, "target_project_path": plan.get("target_project_path")}}

    def _plan(self, repo_root: Path, context: dict) -> dict:
        service_file = repo_root / "factory" / "skills" / "internos" / "vertical_apps4all_module_clone" / "apps4all_module_clone_plan" / "service.py"
        spec = importlib.util.spec_from_file_location("_apps4all_module_clone_plan_service", service_file)
        if spec is None or spec.loader is None:
            return {"ok": False, "error": "apps4all_module_clone_plan no disponible"}
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.Apps4AllModuleClonePlanService().ejecutar(context)

    def _guard(self, repo_root: Path, source_path: Path, target_path: Path) -> dict:
        try:
            source_path.resolve().relative_to(repo_root.resolve())
            target_path.resolve().relative_to(repo_root.resolve())
        except ValueError:
            return {"ok": False, "error": "source/target fuera del repo"}
        if not source_path.exists():
            return {"ok": False, "error": "source_project_path no existe"}
        if source_path.resolve() == target_path.resolve():
            return {"ok": False, "error": "target igual a source"}
        return {"ok": True}

    def _replace(self, text: str, replacements: dict) -> str:
        for old, new in replacements.items():
            text = text.replace(str(old), str(new))
        return text

    def _is_text(self, path: Path) -> bool:
        return path.suffix.lower() in {".ts", ".tsx", ".js", ".jsx", ".json", ".md", ".mjs", ".cjs", ".css", ".html", ".txt", ".example", ".sql", ".py"}
