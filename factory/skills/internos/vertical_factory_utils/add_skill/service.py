"""Service for add_skill - imports external portable skills into Factory."""

from __future__ import annotations

import importlib.util
import json
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path
from urllib.parse import unquote, urlparse

from templates import instruction_service_py, module_service_py, skill_py

_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_-]*$")


class AddSkillService:

    def ejecutar(self, context: dict) -> dict:
        valido, error = self._validar(context)
        if not valido:
            return {"ok": False, "error": error}

        if context.get("dry_run", True):
            return self._planear(context)

        return self._instalar(context)

    # --- validacion ---

    def _validar(self, context: dict) -> tuple[bool, str | None]:
        if not isinstance(context, dict):
            return False, "context debe ser un diccionario"
        nombre = context.get("nombre")
        if not nombre:
            return False, "nombre es requerido"
        if not isinstance(nombre, str):
            return False, "nombre debe ser texto"
        source_path = context.get("path")
        url = context.get("url")
        if not source_path and not url:
            return False, "path local o url es requerido"
        if source_path and not isinstance(source_path, str):
            return False, "path debe ser texto"
        if url and not isinstance(url, str):
            return False, "url debe ser texto"
        if source_path and not Path(source_path).exists():
            return False, f"path no existe: {source_path}"
        if source_path and url:
            return False, "usa path o url, no ambos"
        if url:
            parsed = urlparse(url)
            if parsed.scheme and parsed.scheme not in ("http", "https", "file"):
                return False, "url debe usar http, https o file"
        if not isinstance(context.get("dry_run", True), bool):
            return False, "dry_run debe ser booleano"
        return True, None

    # --- scaffold ---

    def _planear(self, context: dict) -> dict:
        base_dir = Path(context.get("base_dir", "factory"))
        nombre = context["nombre"]

        source_result = self._resolver_origen(context, base_dir)
        if not source_result["ok"]:
            return source_result

        source_path = Path(source_result["data"]["source_path"])
        validation = self._validar_skill_portable(source_path, allow_write=False)
        if not validation["ok"]:
            return validation

        kind = self._resolver_kind(context, validation["data"])
        target_path = base_dir / "skills" / "externos" / self._kind_folder(kind) / nombre

        security_result = self._run_security_gate(context, base_dir, source_path)
        if not security_result["ok"]:
            return security_result

        return {
            "ok": True,
            "message": "plan de importacion generado; no se escribio nada",
            "data": {
                "nombre": nombre,
                "source_path": str(source_path),
                "import_path": source_result["data"].get("import_path"),
                "source_type": source_result["data"]["source_type"],
                "kind": kind,
                "target_path": str(target_path),
                "exists": target_path.exists(),
                "files": validation["data"]["files"],
                "root_detection": source_result["data"].get("root_detection"),
                "wrapper": validation["data"].get("wrapper"),
                "security": security_result["data"],
            },
        }

    def _instalar(self, context: dict) -> dict:
        base_dir = Path(context.get("base_dir", "factory"))
        nombre = context["nombre"]

        source_result = self._resolver_origen(context, base_dir)
        if not source_result["ok"]:
            return source_result

        source_path = Path(source_result["data"]["source_path"])
        validation = self._validar_skill_portable(source_path, allow_write=True)
        if not validation["ok"]:
            return validation

        kind = self._resolver_kind(context, validation["data"])
        target_path = base_dir / "skills" / "externos" / self._kind_folder(kind) / nombre

        security_result = self._run_security_gate(context, base_dir, source_path)
        if not security_result["ok"]:
            return security_result

        if target_path.exists():
            return {"ok": False, "error": f"skill externo ya existe: {target_path}"}

        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source_path, target_path)

        registry_result = self._registrar(context, kind)
        if not registry_result["ok"]:
            return registry_result

        return {
            "ok": True,
            "message": "skill externo importado y registrado",
            "data": {
                "source_path": str(source_path),
                "import_path": source_result["data"].get("import_path"),
                "source_type": source_result["data"]["source_type"],
                "kind": kind,
                "target_path": str(target_path),
                "security": security_result["data"],
                "registry": registry_result["data"],
            },
        }

    # --- validacion de skill portable ---

    def _validar_skill_portable(self, source_path: Path, allow_write: bool) -> dict:
        if not source_path.is_dir():
            return {"ok": False, "error": f"path no es carpeta: {source_path}"}
        if not (source_path / "SKILL.md").exists():
            return {"ok": False, "error": f"falta SKILL.md en {source_path}"}

        wrapper = {"ok": True, "data": {"created": False, "entrypoint": "skill.py"}}
        if not (source_path / "skill.py").exists():
            wrapper = self._crear_wrapper(source_path, allow_write)
            if not wrapper["ok"]:
                return wrapper

        if not (source_path / "service.py").exists() and allow_write:
            self._ensure_service_py(source_path, wrapper["data"])

        files = [
            str(path.relative_to(source_path))
            for path in source_path.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts
        ]
        return {"ok": True, "data": {"files": files, "wrapper": wrapper["data"]}}

    def _crear_wrapper(self, source_path: Path, allow_write: bool) -> dict:
        scripts_dir = source_path / "scripts"
        script_files = (
            [
                path
                for path in scripts_dir.rglob("*.py")
                if path.name != "__init__.py" and "__pycache__" not in path.parts
            ]
            if scripts_dir.is_dir()
            else []
        )

        mode = "instruction_only" if not script_files else (
            None if len(script_files) != 1 else "module"
        )
        if mode is None:
            return {
                "ok": False,
                "error": "falta skill.py y no se pudo inferir un unico script principal",
                "data": {"scripts": [str(p.relative_to(source_path)) for p in script_files]},
            }

        module_path = (
            ".".join(script_files[0].relative_to(source_path).with_suffix("").parts)
            if mode == "module"
            else None
        )

        if not allow_write:
            return {"ok": True, "data": {"created": False, "pending": True, "entrypoint": "skill.py", "mode": mode, "module": module_path}}

        (source_path / "skill.py").write_text(skill_py.render("ImportedSkill"), encoding="utf-8")
        service_content = (
            module_service_py.render("ImportedSkill", module_path)
            if mode == "module"
            else instruction_service_py.render()
        )
        (source_path / "service.py").write_text(service_content, encoding="utf-8")

        return {"ok": True, "data": {"created": True, "entrypoint": "skill.py", "mode": mode, "module": module_path}}

    def _ensure_service_py(self, source_path: Path, wrapper_data: dict) -> None:
        mode = wrapper_data.get("mode", "instruction_only")
        module_path = wrapper_data.get("module")
        content = (
            module_service_py.render("ImportedSkill", module_path)
            if mode == "module" and module_path
            else instruction_service_py.render()
        )
        (source_path / "service.py").write_text(content, encoding="utf-8")

    # --- security gate ---

    def _run_security_gate(self, context: dict, base_dir: Path, source_path: Path) -> dict:
        if context.get("skip_security"):
            return {"ok": True, "data": {"skipped": True, "verdict": "SKIPPED", "summary": {}}}

        gate_path = base_dir / "skills" / "internos" / "security_gate" / "skill.py"
        if not gate_path.exists():
            return {"ok": False, "error": f"security_gate no encontrado: {gate_path}"}

        spec = importlib.util.spec_from_file_location("factory_security_gate", gate_path)
        if spec is None or spec.loader is None:
            return {"ok": False, "error": "no se pudo cargar security_gate"}

        gate_root = str(gate_path.parent)
        saved_scripts = {k: v for k, v in sys.modules.items() if k == "scripts" or k.startswith("scripts.")}
        for name in saved_scripts:
            sys.modules.pop(name, None)

        inserted = gate_root not in sys.path
        if inserted:
            sys.path.insert(0, gate_root)

        try:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            result = module.run({"path": str(source_path), "strict": context.get("strict_security", False)})
        finally:
            if inserted and sys.path and sys.path[0] == gate_root:
                sys.path.pop(0)
            for name in list(sys.modules):
                if name == "scripts" or name.startswith("scripts."):
                    sys.modules.pop(name, None)
            sys.modules.update(saved_scripts)

        if not isinstance(result, dict):
            return {"ok": False, "error": "security_gate no devolvio dict"}
        if result.get("verdict") == "FAIL":
            return {"ok": False, "error": "security_gate bloqueo el skill externo", "data": result}

        return {"ok": True, "data": result}

    # --- origen ---

    def _resolver_origen(self, context: dict, base_dir: Path) -> dict:
        if context.get("path"):
            source_path = Path(context["path"]).resolve()
            skill_root = self._detectar_skill_root(source_path)
            if not skill_root["ok"]:
                return skill_root
            return {"ok": True, "data": {"source_type": "path", "source_path": str(skill_root["data"]["skill_root"]), "root_detection": skill_root["data"]}}

        return self._preparar_url(context, base_dir)

    def _preparar_url(self, context: dict, base_dir: Path) -> dict:
        nombre = context["nombre"]
        url = context["url"]
        imports_dir = base_dir / "workspace" / "imports"
        import_path = imports_dir / nombre
        download_path = imports_dir / f"{nombre}.download"

        if import_path.exists():
            return {"ok": False, "error": f"import en workspace ya existe: {import_path}"}

        imports_dir.mkdir(parents=True, exist_ok=True)
        parsed = urlparse(url)
        git_tree = self._parse_git_tree_url(parsed)

        try:
            if self._es_zip_url(url, parsed):
                self._descargar_archivo(url, parsed, download_path)
                import_path.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(download_path) as zf:
                    zf.extractall(import_path)
                download_path.unlink(missing_ok=True)
            else:
                clone_url = git_tree["repo_url"] if git_tree else url
                cmd = ["git", "clone", "--depth", "1"]
                if git_tree and git_tree["ref"] != "HEAD":
                    cmd.extend(["--branch", git_tree["ref"]])
                cmd.extend([clone_url, str(import_path)])
                subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as exc:
            return {"ok": False, "error": f"no se pudo clonar url: {exc.stderr.strip() or exc}"}
        except (OSError, zipfile.BadZipFile) as exc:
            return {"ok": False, "error": f"no se pudo preparar url: {exc}"}

        detect_base = import_path
        if git_tree:
            detect_base = import_path / git_tree["subpath"]
            if not detect_base.exists():
                return {"ok": False, "error": f"subcarpeta del skill no existe en repo: {git_tree['subpath']}"}

        skill_root = self._detectar_skill_root(detect_base)
        if not skill_root["ok"]:
            return skill_root

        return {
            "ok": True,
            "data": {
                "source_type": "url",
                "source_path": str(skill_root["data"]["skill_root"]),
                "import_path": str(import_path),
                "url_subpath": git_tree["subpath"] if git_tree else "",
                "root_detection": skill_root["data"],
            },
        }

    def _detectar_skill_root(self, source_path: Path) -> dict:
        if not source_path.is_dir():
            return {"ok": False, "error": f"path no es carpeta: {source_path}"}
        if (source_path / "SKILL.md").exists():
            return {"ok": True, "data": {"skill_root": str(source_path.resolve()), "detected_from": str(source_path.resolve()), "nested": False}}

        matches = sorted(
            [p.parent for p in source_path.rglob("SKILL.md") if ".git" not in p.parts],
            key=lambda p: len(p.relative_to(source_path).parts),
        )
        if not matches:
            return {"ok": False, "error": f"falta SKILL.md en {source_path}"}

        skill_root = matches[0].resolve()
        return {"ok": True, "data": {"skill_root": str(skill_root), "detected_from": str(source_path.resolve()), "nested": skill_root != source_path.resolve()}}

    # --- registry ---

    def _registrar(self, context: dict, kind: str) -> dict:
        base_dir = Path(context.get("base_dir", "factory"))
        registry_path = base_dir / "skills" / "registry.json"
        nombre = context["nombre"]

        registry = self._load_registry(registry_path)
        entry = {
            "tipo": "externo",
            "nombre": nombre,
            "kind": kind,
            "vertical": context.get("vertical", "external"),
            "descripcion": context.get("descripcion", f"Skill externo {nombre}"),
            "path": f"skills/externos/{self._kind_folder(kind)}/{nombre}",
            "entrypoint": "skill.py",
            "version": context.get("version", "0.1.0"),
        }
        registry[nombre] = entry
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        registry_path.write_text(json.dumps(registry, indent=2, ensure_ascii=False), encoding="utf-8")
        return {"ok": True, "data": {"registry_path": str(registry_path), "entry": entry}}

    def _load_registry(self, registry_path: Path) -> dict:
        if not registry_path.exists():
            return {}
        for encoding in ("utf-8", "utf-8-sig", "utf-16"):
            try:
                raw = registry_path.read_text(encoding=encoding).strip()
                return json.loads(raw) if raw else {}
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
        return {}

    # --- helpers ---

    def _parse_git_tree_url(self, parsed) -> dict | None:
        if parsed.netloc.lower() != "github.com":
            return None
        parts = [p for p in parsed.path.split("/") if p]
        if len(parts) < 5 or parts[2] != "tree":
            return None
        owner, repo, _, ref = parts[:4]
        return {"repo_url": f"https://github.com/{owner}/{repo}.git", "ref": ref, "subpath": str(Path(*parts[4:]))}

    def _es_zip_url(self, url: str, parsed) -> bool:
        return parsed.scheme == "file" or parsed.path.lower().endswith(".zip")

    def _descargar_archivo(self, url: str, parsed, download_path: Path) -> None:
        if parsed.scheme == "file":
            local_path = Path(unquote(parsed.path.lstrip("/"))).resolve()
            if not local_path.exists():
                raise OSError(f"archivo local no existe: {local_path}")
            shutil.copyfile(local_path, download_path)
            return
        with urllib.request.urlopen(url) as response:
            with download_path.open("wb") as target:
                shutil.copyfileobj(response, target)

    def _resolver_kind(self, context: dict, validation_data: dict) -> str:
        requested = context.get("kind", "auto")
        if requested in ("instruction_only", "instructions", "instrucciones"):
            return "instruction_only"
        if requested in ("executable", "ejecutable"):
            return "executable"
        wrapper = validation_data.get("wrapper", {})
        if wrapper.get("mode") == "instruction_only":
            return "instruction_only"
        return "executable"

    def _kind_folder(self, kind: str) -> str:
        return "instrucciones" if kind == "instruction_only" else "ejecutables"
