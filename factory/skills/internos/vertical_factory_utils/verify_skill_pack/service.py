"""Service for verify_skill_pack - validates exported skill packs."""

from __future__ import annotations

import json
from pathlib import Path

from factory.engine import SkillLoader


class VerifySkillPackService:

    def ejecutar(self, context: dict) -> dict:
        pack_dir = Path(context.get("pack_dir", ""))
        if not str(pack_dir):
            return {"ok": False, "error": "pack_dir es requerido"}

        checks: list[dict] = []
        self._check(checks, "pack directory exists", lambda: self._exists_dir(pack_dir))
        self._check(checks, "pack manifest exists", lambda: self._exists_file(pack_dir / "pack_manifest.json"))
        self._check(checks, "skills registry exists", lambda: self._exists_file(pack_dir / "skills" / "registry.json"))
        self._check(checks, "registry is valid", lambda: self._validate_registry(pack_dir))
        self._check(checks, "skill folders exist", lambda: self._validate_skill_folders(pack_dir))
        self._check(checks, "skill loader can inspect", lambda: self._validate_loader(pack_dir))

        failures = [check for check in checks if not check["ok"]]
        return {
            "ok": not failures,
            "message": "skill pack OK" if not failures else "skill pack tiene fallas",
            "data": {
                "pack_dir": str(pack_dir),
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

    def _validate_registry(self, pack_dir: Path) -> None:
        registry = self._load_registry(pack_dir)
        if not registry:
            raise RuntimeError("registry vacio")
        manifest_path = pack_dir / "pack_manifest.json"
        manifest = self._load_json(manifest_path)
        skills = manifest.get("skills", [])
        if skills and sorted(skills) != sorted(registry):
            raise RuntimeError("pack_manifest.skills no coincide con skills/registry.json")

    def _validate_skill_folders(self, pack_dir: Path) -> None:
        registry = self._load_registry(pack_dir)
        missing = []
        for name, entry in registry.items():
            relative = entry.get("path", f"skills/internos/{name}")
            skill_path = pack_dir / relative
            if not skill_path.exists():
                skill_path = pack_dir / "skills" / "internos" / name
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

    def _validate_loader(self, pack_dir: Path) -> None:
        registry = self._load_registry(pack_dir)
        loader = SkillLoader(pack_dir / "skills" / "internos", pack_dir / "skills" / "externos")
        failures = []
        for name in registry:
            try:
                loader.inspect(name, "internos")
            except Exception as exc:  # noqa: BLE001
                failures.append(f"{name}: {exc}")
        if failures:
            raise RuntimeError("; ".join(failures))

    def _load_registry(self, pack_dir: Path) -> dict:
        return self._load_json(pack_dir / "skills" / "registry.json")

    def _load_json(self, path: Path) -> dict:
        if not path.exists():
            return {}
        raw = path.read_text(encoding="utf-8-sig", errors="replace").strip()
        if not raw:
            return {}
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
