"""Service for verify_new_factory - validates generated factory folders."""

from __future__ import annotations

import json
from pathlib import Path

from factory.engine import SkillLoader


TEXT_SUFFIXES = {".py", ".json", ".md", ".txt", ".yml", ".yaml", ".toml", ".ini", ".env", ".example"}
FORBIDDEN_GENERIC_TERMS = ["Factory", "FACTORY", "factory", "factory"]


class VerifyNewFactoryService:

    def ejecutar(self, context: dict) -> dict:
        factory_dir = Path(context.get("factory_dir", ""))
        if not str(factory_dir):
            return {"ok": False, "error": "factory_dir es requerido"}

        package_dir = context.get("package_dir", "factory")
        expected_verticals = context.get("verticals", [])
        checks: list[dict] = []

        self._check(checks, "factory directory exists", lambda: self._exists_dir(factory_dir))
        self._check(checks, "package directory exists", lambda: self._exists_dir(factory_dir / package_dir))
        self._check(checks, "skills registry exists", lambda: self._exists_file(self._registry_path(factory_dir, package_dir)))
        self._check(checks, "runtime engine exists", lambda: self._exists_dir(factory_dir / package_dir / "engine"))
        self._check(checks, "api module exists", lambda: self._validate_api_module(factory_dir, context))
        self._check(checks, "registry is valid", lambda: self._validate_registry(factory_dir, package_dir, expected_verticals))
        self._check(checks, "skill folders exist", lambda: self._validate_skill_folders(factory_dir, package_dir))
        self._check(checks, "skill loader can inspect", lambda: self._validate_loader(factory_dir, package_dir))
        self._check(checks, "env example is generic", lambda: self._validate_env_example(factory_dir))
        self._check(checks, "no legacy factory package generated", lambda: self._validate_no_legacy_package(factory_dir, package_dir))
        self._check(checks, "no legacy brand text", lambda: self._validate_no_legacy_text(factory_dir, package_dir))

        failures = [check for check in checks if not check["ok"]]
        return {
            "ok": not failures,
            "message": "new factory OK" if not failures else "new factory tiene fallas",
            "data": {
                "factory_dir": str(factory_dir),
                "package_dir": package_dir,
                "checks": checks,
                "failures": len(failures),
            },
        }

    def _check(self, checks: list[dict], name: str, func) -> None:
        try:
            func()
        except Exception as exc:  # noqa: BLE001 - verifier reports all failures.
            checks.append({"name": name, "ok": False, "error": str(exc)})
        else:
            checks.append({"name": name, "ok": True})

    def _exists_dir(self, path: Path) -> None:
        if not path.exists() or not path.is_dir():
            raise FileNotFoundError(path)

    def _exists_file(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(path)

    def _validate_registry(self, factory_dir: Path, package_dir: str, expected_verticals: list[str]) -> None:
        registry = self._load_registry(factory_dir, package_dir)
        if not registry:
            raise RuntimeError("registry vacio")
        if expected_verticals:
            unexpected = sorted({
                entry.get("vertical", "")
                for entry in registry.values()
                if entry.get("vertical") not in expected_verticals
            })
            if unexpected:
                raise RuntimeError(f"verticales inesperadas: {', '.join(unexpected)}")

    def _validate_skill_folders(self, factory_dir: Path, package_dir: str) -> None:
        registry = self._load_registry(factory_dir, package_dir)
        missing = []
        for name, entry in registry.items():
            relative = entry.get("path", f"skills/internos/{name}")
            skill_path = factory_dir / package_dir / relative
            if not skill_path.exists():
                missing.append(f"{name}: carpeta no existe")
                continue
            if not (skill_path / "manifest.json").exists() and not (skill_path / "SKILL.md").exists():
                missing.append(f"{name}: falta manifest.json o SKILL.md")
                continue
            manifest = self._load_json(skill_path / "manifest.json") if (skill_path / "manifest.json").exists() else {}
            entrypoint = manifest.get("entrypoint", entry.get("entrypoint", "skill.py"))
            kind = manifest.get("kind", "executable")
            if kind == "executable" and not (skill_path / entrypoint).exists():
                missing.append(f"{name}: falta entrypoint {entrypoint}")
        if missing:
            raise RuntimeError("; ".join(missing))

    def _validate_loader(self, factory_dir: Path, package_dir: str) -> None:
        registry = self._load_registry(factory_dir, package_dir)
        loader = SkillLoader(
            factory_dir / package_dir / "skills" / "internos",
            factory_dir / package_dir / "skills" / "externos",
        )
        failures = []
        for name in registry:
            try:
                loader.inspect(name, "internos")
            except Exception as exc:  # noqa: BLE001
                failures.append(f"{name}: {exc}")
        if failures:
            raise RuntimeError("; ".join(failures))

    def _validate_env_example(self, factory_dir: Path) -> None:
        env_path = factory_dir / ".env.example"
        self._exists_file(env_path)
        text = env_path.read_text(encoding="utf-8-sig", errors="replace")
        forbidden = ["ADMIN_BOT_TOKEN", "ADMIN_CHAT_ID"]
        found = [item for item in forbidden if item in text]
        if found:
            raise RuntimeError(f"env legacy encontrado: {', '.join(found)}")
        if "factory_telegram" in text:
            required = ["ADMIN_BOT_TOKEN", "ADMIN_CHAT_ID"]
            missing = [item for item in required if item not in text]
            if missing:
                raise RuntimeError(f"env admin faltante: {', '.join(missing)}")

    def _validate_no_legacy_package(self, factory_dir: Path, package_dir: str) -> None:
        if package_dir != "factory" and (factory_dir / "factory").exists():
            raise RuntimeError("se genero carpeta legacy factory")

    def _validate_api_module(self, factory_dir: Path, context: dict) -> None:
        api_module = context.get("api_module", "factory_api:app")
        api_file = api_module.split(":", 1)[0] + ".py"
        self._exists_file(factory_dir / api_file)

    def _validate_no_legacy_text(self, factory_dir: Path, package_dir: str) -> None:
        if package_dir == "factory":
            return
        hits = []
        for path in factory_dir.rglob("*"):
            if not path.is_file() or not self._is_text_path(path):
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for term in FORBIDDEN_GENERIC_TERMS:
                if term in text:
                    hits.append(f"{path.relative_to(factory_dir)}: {term}")
                    break
            if len(hits) >= 20:
                break
        if hits:
            raise RuntimeError("; ".join(hits))

    def _registry_path(self, factory_dir: Path, package_dir: str) -> Path:
        return factory_dir / package_dir / "skills" / "registry.json"

    def _load_registry(self, factory_dir: Path, package_dir: str) -> dict:
        return self._load_json(self._registry_path(factory_dir, package_dir))

    def _load_json(self, path: Path) -> dict:
        if not path.exists():
            return {}
        raw = path.read_text(encoding="utf-8-sig", errors="replace").strip()
        if not raw:
            return {}
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}

    def _is_text_path(self, path: Path) -> bool:
        if path.name.endswith(".env.example"):
            return True
        return path.suffix.lower() in TEXT_SUFFIXES
