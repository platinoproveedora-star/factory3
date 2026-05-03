"""Service for verify_factory - local checks for Factory."""

from __future__ import annotations

import compileall
import json
import shutil
import sys
import traceback
from pathlib import Path
from typing import Callable


class VerifyFactoryService:

    def ejecutar(self, context: dict) -> dict:
        root = self._root(context)
        factory_dir = root / "factory"
        tmp_dir = root / "tmp" / "verify_factory"
        verbose = bool(context.get("verbose", False))

        if str(root) not in sys.path:
            sys.path.insert(0, str(root))

        self._clean_tmp(tmp_dir)
        checks: list[dict] = []

        self._check(checks, "compile core factory skills", lambda: self._compile_core_skills(factory_dir))
        self._check(checks, "inspect skills registry", lambda: self._inspect_registry_skills(factory_dir))
        self._check(checks, "inspect agents registry", lambda: self._inspect_agents_registry(factory_dir))
        self._check(checks, "load internal executable skills", lambda: self._load_internal_skills(factory_dir))
        self._check(checks, "dry-run factory generators", lambda: self._dry_run_generators(factory_dir, tmp_dir))
        self._check(checks, "generated skill and agent load", lambda: self._generated_units_load(factory_dir, tmp_dir))
        self._check(checks, "agent brain loader", lambda: self._agent_brain_loader_check(factory_dir, tmp_dir))
        self._check(checks, "bot connected agent brain routing", lambda: self._bot_brain_routing_check(root, factory_dir, tmp_dir))

        self._clean_tmp(tmp_dir)

        failures = [check for check in checks if not check["ok"]]
        result = {
            "ok": not failures,
            "message": "verify_factory OK" if not failures else "verify_factory encontro fallas",
            "data": {
                "root": str(root),
                "checks": checks,
                "failures": len(failures),
            },
        }
        if verbose and failures:
            result["data"]["tracebacks"] = [check.get("traceback") for check in failures if check.get("traceback")]
        return result

    def _check(self, checks: list[dict], name: str, func: Callable[[], None]) -> None:
        try:
            func()
        except Exception as exc:  # noqa: BLE001 - verifier reports all check failures.
            checks.append(
                {
                    "name": name,
                    "ok": False,
                    "error": str(exc),
                    "traceback": traceback.format_exc(),
                }
            )
        else:
            checks.append({"name": name, "ok": True})

    def _compile_core_skills(self, factory_dir: Path) -> None:
        paths = [
            factory_dir / "engine",
            factory_dir / "skills" / "internos" / "new_skill",
            factory_dir / "skills" / "internos" / "new_agent",
            factory_dir / "skills" / "internos" / "add_skill",
            factory_dir / "skills" / "internos" / "add_bot",
            factory_dir / "skills" / "internos" / "security_gate",
            factory_dir / "skills" / "internos" / "verify_factory",
            factory_dir / "skills" / "internos" / "connect_bot_agent",
            factory_dir / "skills" / "internos" / "add_agent_brain",
        ]
        for path in paths:
            if not path.exists():
                raise FileNotFoundError(path)
            if not compileall.compile_dir(path, quiet=1):
                raise RuntimeError(f"compileall failed: {path}")

    def _inspect_registry_skills(self, factory_dir: Path) -> None:
        from factory.engine.skill_loader import SkillLoader

        registry = self._read_registry(factory_dir)
        loader = SkillLoader(factory_dir / "skills" / "internos", factory_dir / "skills" / "externos")
        missing: list[str] = []
        for name, entry in registry.items():
            source = entry.get("tipo", "internos")
            try:
                loader.inspect(name, source)
            except Exception as exc:  # noqa: BLE001
                missing.append(f"{name}: {exc}")
        if missing:
            raise RuntimeError("; ".join(missing))

    def _inspect_agents_registry(self, factory_dir: Path) -> None:
        from factory.engine.agent_loader import AgentLoader

        registry_path = factory_dir / "agents" / "registry.json"
        raw = registry_path.read_text(encoding="utf-8") if registry_path.exists() else "{}"
        registry = json.loads(raw) if raw.strip() else {}
        if not isinstance(registry, dict):
            raise RuntimeError("agents registry must be a JSON object")

        loader = AgentLoader(factory_dir / "agents")
        missing: list[str] = []
        for name in registry:
            try:
                loader.inspect(name)
            except Exception as exc:  # noqa: BLE001
                missing.append(f"{name}: {exc}")
        if missing:
            raise RuntimeError("; ".join(missing))

    def _load_internal_skills(self, factory_dir: Path) -> None:
        from factory.engine.skill_loader import SkillLoader

        registry = self._read_registry(factory_dir)
        loader = SkillLoader(factory_dir / "skills" / "internos", factory_dir / "skills" / "externos")
        failures: list[str] = []
        for name, entry in registry.items():
            if entry.get("tipo") != "interno":
                continue
            spec = loader.inspect(name, "internos")
            if spec.kind != "executable":
                continue
            try:
                module = loader.load_module(spec)
            except Exception as exc:  # noqa: BLE001
                failures.append(f"{name}: {exc}")
                continue
            if not callable(getattr(module, "run", None)):
                failures.append(f"{name}: missing run(context)")
        if failures:
            raise RuntimeError("; ".join(failures))

    def _dry_run_generators(self, factory_dir: Path, tmp_dir: Path) -> None:
        from factory.engine.skill_loader import SkillLoader
        from factory.engine.skill_runner import SkillRunner

        loader = SkillLoader(factory_dir / "skills" / "internos", factory_dir / "skills" / "externos")
        runner = SkillRunner(loader)
        contexts = {
            "new_skill": {
                "nombre": "verify_skill",
                "vertical": "qa",
                "descripcion": "Verification skill",
                "dry_run": True,
                "base_dir": str(tmp_dir),
            },
            "new_agent": {
                "nombre": "verify_agent",
                "vertical": "qa",
                "descripcion": "Verification agent",
                "mcps": "telegram",
                "skills": "new_skill",
                "dry_run": True,
                "base_dir": str(tmp_dir),
            },
            "add_bot": {
                "bot_name": "verify_bot",
                "bot_type": "admin",
                "token_env": "VERIFY_BOT_TOKEN",
                "admin_chat_id": "",
                "empresa": "factory",
                "commands": "start,ayuda",
                "dry_run": True,
                "base_dir": str(tmp_dir),
            },
        }

        source_skill = self._make_external_skill_source(tmp_dir)
        contexts["add_skill"] = {
            "nombre": "verify_external_skill",
            "path": str(source_skill),
            "dry_run": True,
            "base_dir": str(factory_dir),
        }
        self._make_connect_fixture(tmp_dir)
        contexts["connect_bot_agent"] = {
            "bot_name": "verify_bot",
            "agent_name": "verify_agent",
            "mode": "chat",
            "dry_run": True,
            "base_dir": str(tmp_dir),
        }
        contexts["add_agent_brain"] = {
            "agent_name": "verify_agent",
            "system_prompt": "Eres un agente temporal de verificacion.",
            "dry_run": True,
            "base_dir": str(tmp_dir),
        }

        failures: list[str] = []
        for name, generator_context in contexts.items():
            result = runner.run(name, generator_context)
            if not result.get("ok"):
                failures.append(f"{name}: {result.get('error', result)}")
        if failures:
            raise RuntimeError("; ".join(failures))

    def _generated_units_load(self, factory_dir: Path, tmp_dir: Path) -> None:
        from factory.engine.agent_loader import AgentLoader
        from factory.engine.skill_loader import SkillLoader
        from factory.engine.skill_runner import SkillRunner

        internal_loader = SkillLoader(factory_dir / "skills" / "internos", factory_dir / "skills" / "externos")
        runner = SkillRunner(internal_loader)

        skill_result = runner.run(
            "new_skill",
            {
                "nombre": "verify_generated_skill",
                "vertical": "qa",
                "descripcion": "Generated verification skill",
                "dry_run": False,
                "base_dir": str(tmp_dir),
            },
        )
        if not skill_result.get("ok"):
            raise RuntimeError(f"new_skill create failed: {skill_result}")

        agent_result = runner.run(
            "new_agent",
            {
                "nombre": "verify_generated_agent",
                "vertical": "qa",
                "descripcion": "Generated verification agent",
                "mcps": "telegram",
                "skills": "verify_generated_skill",
                "dry_run": False,
                "base_dir": str(tmp_dir),
            },
        )
        if not agent_result.get("ok"):
            raise RuntimeError(f"new_agent create failed: {agent_result}")

        generated_skill_loader = SkillLoader(tmp_dir / "skills" / "internos")
        skill_module = generated_skill_loader.load_module(generated_skill_loader.inspect("verify_generated_skill"))
        skill_run = skill_module.run({"source": "verify_factory"})
        if not skill_run.get("ok"):
            raise RuntimeError(f"generated skill run failed: {skill_run}")

        generated_agent_loader = AgentLoader(tmp_dir / "agents")
        agent_module = generated_agent_loader.load_module(generated_agent_loader.inspect("verify_generated_agent"))
        agent_run = agent_module.run({"source": "verify_factory"})
        if not agent_run.get("ok"):
            raise RuntimeError(f"generated agent run failed: {agent_run}")

    def _agent_brain_loader_check(self, factory_dir: Path, tmp_dir: Path) -> None:
        from factory.engine import AgentBrainLoader
        from factory.engine.skill_loader import SkillLoader
        from factory.engine.skill_runner import SkillRunner

        internal_loader = SkillLoader(factory_dir / "skills" / "internos", factory_dir / "skills" / "externos")
        runner = SkillRunner(internal_loader)

        agent_name = "verify_brain_agent"
        agent_result = runner.run(
            "new_agent",
            {
                "nombre": agent_name,
                "vertical": "qa",
                "descripcion": "Generated brain verification agent",
                "dry_run": False,
                "base_dir": str(tmp_dir),
            },
        )
        if not agent_result.get("ok"):
            raise RuntimeError(f"new_agent create failed: {agent_result}")

        brain_result = runner.run(
            "add_agent_brain",
            {
                "agent_name": agent_name,
                "system_prompt": "Eres un agente temporal de verificacion.",
                "dry_run": False,
                "base_dir": str(tmp_dir),
            },
        )
        if not brain_result.get("ok"):
            raise RuntimeError(f"add_agent_brain failed: {brain_result}")

        response = AgentBrainLoader(tmp_dir / "agents").respond(agent_name, "hola", {"source": "verify_factory"})
        if response.get("ok"):
            raise RuntimeError("agent brain should not call Anthropic without ANTHROPIC_API_KEY in verifier")
        if "ANTHROPIC_API_KEY" not in response.get("error", ""):
            raise RuntimeError(f"unexpected agent brain error: {response}")

    def _bot_brain_routing_check(self, root: Path, factory_dir: Path, tmp_dir: Path) -> None:
        from factory.engine.skill_loader import SkillLoader
        from factory.engine.skill_runner import SkillRunner

        internal_loader = SkillLoader(factory_dir / "skills" / "internos", factory_dir / "skills" / "externos")
        runner = SkillRunner(internal_loader)

        agent_name = "verify_bot_agent"
        agent_result = runner.run(
            "new_agent",
            {
                "nombre": agent_name,
                "vertical": "qa",
                "descripcion": "Generated bot routing verification agent",
                "dry_run": False,
                "base_dir": str(tmp_dir),
            },
        )
        if not agent_result.get("ok"):
            raise RuntimeError(f"new_agent create failed: {agent_result}")

        brain_result = runner.run(
            "add_agent_brain",
            {
                "agent_name": agent_name,
                "system_prompt": "Eres un agente temporal de verificacion.",
                "dry_run": False,
                "base_dir": str(tmp_dir),
            },
        )
        if not brain_result.get("ok"):
            raise RuntimeError(f"add_agent_brain failed: {brain_result}")

        bot_src = factory_dir / "bots" / "factory_admin"
        bot_name = "verify_brain_bot"
        bot_dst = tmp_dir / "bots" / bot_name
        if bot_dst.exists():
            shutil.rmtree(bot_dst)
        shutil.copytree(bot_src, bot_dst, ignore=shutil.ignore_patterns("__pycache__"))
        config_path = bot_dst / "config.json"
        config = self._load_json(config_path)
        config["bot_name"] = bot_name
        self._write_json(config_path, config)
        (tmp_dir / "bots" / "registry.json").write_text(
            json.dumps(
                {
                    bot_name: {
                        "nombre": bot_name,
                        "path": f"bots/{bot_name}",
                        "entrypoint": "bot.py",
                    }
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        connect_result = runner.run(
            "connect_bot_agent",
            {
                "bot_name": bot_name,
                "agent_name": agent_name,
                "mode": "chat",
                "dry_run": False,
                "base_dir": str(tmp_dir),
            },
        )
        if not connect_result.get("ok"):
            raise RuntimeError(f"connect_bot_agent failed: {connect_result}")

        bot_path = str(bot_dst)
        for module_name in list(sys.modules):
            if module_name == "bot" or module_name.startswith("scripts."):
                sys.modules.pop(module_name, None)
        sys.path.insert(0, bot_path)
        try:
            from bot import handle_update

            result = handle_update(
                {
                    "message": {
                        "text": "hola",
                        "chat": {"id": 1},
                        "from": {"id": 2},
                    }
                },
                {},
            )
        finally:
            if sys.path and sys.path[0] == bot_path:
                sys.path.pop(0)
            sys.modules.pop("bot", None)
            for module_name in list(sys.modules):
                if module_name.startswith("scripts."):
                    sys.modules.pop(module_name, None)
            self._purge_modules_from_path(bot_dst)

        response = result.get("response", "") if isinstance(result, dict) else ""
        expected = f"Error del agente {agent_name}: ANTHROPIC_API_KEY no configurada"
        if response != expected:
            raise RuntimeError(f"unexpected bot brain response: {result}")

    def _make_external_skill_source(self, tmp_dir: Path) -> Path:
        source = tmp_dir / "external_source" / "verify_external_skill"
        source.mkdir(parents=True, exist_ok=True)
        (source / "SKILL.md").write_text(
            """---
name: verify_external_skill
description: External skill fixture for verifier
version: "0.1.0"
type: external
entrypoint: skill.py
---
""",
            encoding="utf-8",
        )
        (source / "skill.py").write_text(
            """def run(context):
    return {"ok": True, "data": {"received_context": context}}
""",
            encoding="utf-8",
        )
        return source

    def _make_connect_fixture(self, tmp_dir: Path) -> None:
        bot_path = tmp_dir / "bots" / "verify_bot"
        agent_path = tmp_dir / "agents" / "verify_agent"
        bot_path.mkdir(parents=True, exist_ok=True)
        agent_path.mkdir(parents=True, exist_ok=True)
        (bot_path / "config.json").write_text(
            json.dumps({"bot_name": "verify_bot"}, indent=2) + "\n",
            encoding="utf-8",
        )
        (bot_path / "manifest.json").write_text(
            json.dumps({"type": "bot", "name": "verify_bot", "entrypoint": "bot.py"}, indent=2) + "\n",
            encoding="utf-8",
        )
        (agent_path / "SKILL.md").write_text("# verify_agent\n", encoding="utf-8")
        (agent_path / "manifest.json").write_text(
            json.dumps({"type": "agent", "name": "verify_agent", "entrypoint": "agent.py"}, indent=2) + "\n",
            encoding="utf-8",
        )
        (agent_path / "agent.py").write_text("def run(context):\n    return {'ok': True}\n", encoding="utf-8")
        (tmp_dir / "bots" / "registry.json").write_text(
            json.dumps(
                {
                    "verify_bot": {
                        "nombre": "verify_bot",
                        "path": "bots/verify_bot",
                        "entrypoint": "bot.py",
                    }
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (tmp_dir / "agents" / "registry.json").write_text(
            json.dumps(
                {
                    "verify_agent": {
                        "nombre": "verify_agent",
                        "path": "agents/verify_agent",
                        "entrypoint": "agent.py",
                    }
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    def _read_registry(self, factory_dir: Path) -> dict:
        raw = (factory_dir / "skills" / "registry.json").read_text(encoding="utf-8")
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise RuntimeError("skills registry must be a JSON object")
        return data

    def _load_json(self, path: Path) -> dict:
        if not path.exists():
            return {}
        raw = path.read_text(encoding="utf-8-sig", errors="replace").strip()
        if not raw:
            return {}
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}

    def _write_json(self, path: Path, data: dict) -> None:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def _purge_modules_from_path(self, path: Path) -> None:
        root = path.resolve()
        for name, module in list(sys.modules.items()):
            module_file = getattr(module, "__file__", None)
            if not module_file:
                continue
            try:
                Path(module_file).resolve().relative_to(root)
            except ValueError:
                continue
            sys.modules.pop(name, None)

    def _clean_tmp(self, tmp_dir: Path) -> None:
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)

    def _root(self, context: dict) -> Path:
        if context.get("base_dir"):
            return Path(context["base_dir"]).resolve()
        return Path(__file__).resolve().parents[4]
