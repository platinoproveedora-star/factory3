"""Test runner automático para los 6 skills críticos de campaña."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import traceback
from pathlib import Path
from datetime import datetime, timezone

_INTERNOS = Path(__file__).resolve().parents[1]  # factory/skills/internos
_SEMAFORO    = {"pass": "PASS", "fail": "FAIL", "skip": "SKIP", "warn": "WARN"}

# Suites de tests por skill crítico
_TEST_SUITES: dict[str, list[dict]] = {
    "qa_preflight": [
        {
            "name": "campos mínimos con skip_url_checks",
            "context": {
                "company_id": "TEST", "campaign_id": "camp_test",
                "skip_url_checks": True,
                "landing_url": "", "whatsapp_link": "", "privacy_url": "",
                "image_url": "", "daily_budget": 100, "ad_copy": "Texto de prueba del anuncio",
                "approver": "qa_bot", "pixel_id": "PIXEL_TEST",
                "lead_form_id": "TEST_FORM_001",
                "meta_access_token": "FAKE_TOKEN_SKIP",
                "campaign_status": "PAUSED",
            },
            "expect_ok": True,
        },
        {
            "name": "campaign_status ACTIVE debe fallar",
            "context": {
                "company_id": "TEST", "campaign_id": "camp_test",
                "landing_url": "", "whatsapp_link": "", "privacy_url": "",
                "image_url": "", "daily_budget": 100, "ad_copy": "Texto de prueba del anuncio",
                "approver": "qa_bot", "pixel_id": "PIXEL_TEST",
                "campaign_status": "ACTIVE",
            },
            "expect_ok": False,
        },
    ],
    "qa_secrets_check": [
        {
            "name": "verificar categoría core",
            "context": {"categories": ["core"]},
            "expect_keys": ["presentes", "faltantes", "checks"],
        },
        {
            "name": "categoría desconocida (como var directa)",
            "context": {"categories": ["VAR_QUE_NO_EXISTE_XXX"]},
            "expect_keys": ["missing_vars"],
        },
    ],
    "qa_campaign_logger": [
        {
            "name": "log dry_run",
            "context": {
                "action": "log",
                "company_id": "TEST", "campaign_id": "camp_test",
                "skill_name": "meta_ads_publish_flow",
                "status": "ok", "message": "test log",
                "dry_run": True,
            },
            "expect_ok": True,
        },
        {
            "name": "log sin company_id debe fallar",
            "context": {"action": "log", "skill_name": "test"},
            "expect_ok": False,
        },
    ],
    "qa_rollback_campaign": [
        {
            "name": "backup_and_pause dry_run",
            "context": {
                "action": "backup_and_pause",
                "campaign_id": "120208000000",
                "company_id": "TEST",
                "dry_run": True,
            },
            "expect_ok": False,  # sin token real → error esperado
        },
        {
            "name": "restore sin backup_id ni campaign_id debe fallar",
            "context": {"action": "restore"},
            "expect_ok": False,
        },
        {
            "name": "ensure_table dry_run",
            "context": {"action": "ensure_table", "dry_run": True},
            "expect_ok": True,
        },
    ],
    "meta_ads_connection_check": [
        {
            "name": "sin token debe fallar",
            "context": {"access_token": "", "ad_account_id": ""},
            "expect_ok": False,
        },
    ],
    "meta_ads_publish_flow": [
        {
            "name": "dry_run sin campos → error expected",
            "context": {"dry_run": True, "nombre_campana": "", "link": ""},
            "expect_ok": False,
        },
        {
            "name": "dry_run con campos mínimos",
            "context": {
                "dry_run": True,
                "nombre_campana": "QA Test Campaign",
                "link": "https://example.com",
                "daily_budget": 100,
                "access_token": "TOKEN_FAKE",
                "ad_account_id": "act_123456",
                "page_id": "123456",
            },
            "expect_ok": True,
        },
    ],
}


class QASkillsTestService:

    def ejecutar(self, context: dict) -> dict:
        skills_to_test = context.get("skills") or list(_TEST_SUITES.keys())
        if isinstance(skills_to_test, str):
            skills_to_test = [s.strip() for s in skills_to_test.split(",")]

        verbose = bool(context.get("verbose", False))
        results: list[dict] = []

        for skill_name in skills_to_test:
            suites = _TEST_SUITES.get(skill_name)
            if not suites:
                results.append({
                    "skill": skill_name,
                    "status": "skip",
                    "semaforo": _SEMAFORO["skip"],
                    "message": "Sin suite de tests definida",
                    "tests": [],
                })
                continue

            skill_module = self._load_skill(skill_name)
            tests: list[dict] = []

            for suite in suites:
                test_result = self._run_test(skill_module, skill_name, suite, verbose)
                tests.append(test_result)

            passed  = sum(1 for t in tests if t["status"] == "pass")
            failed  = sum(1 for t in tests if t["status"] == "fail")
            status  = "pass" if failed == 0 else "fail"

            results.append({
                "skill":    skill_name,
                "status":   status,
                "semaforo": _SEMAFORO[status],
                "message":  f"{passed}/{len(tests)} tests pasados",
                "tests":    tests,
            })

        total   = len(results)
        passing = sum(1 for r in results if r["status"] == "pass")
        failing = sum(1 for r in results if r["status"] == "fail")
        skipped = sum(1 for r in results if r["status"] == "skip")

        return {
            "ok": failing == 0,
            "message": (
                f"QA Tests OK — {passing}/{total} skills pasando"
                if failing == 0
                else f"QA Tests FALLIDOS — {failing} skills con errores"
            ),
            "data": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "resumen": {
                    "total": total, "pass": passing,
                    "fail": failing, "skip": skipped,
                },
                "skills": results,
            },
        }

    # ── HELPERS ──────────────────────────────────────────────────────────────

    def _load_skill(self, skill_name: str):
        """Carga el módulo skill.py buscando en rutas conocidas."""
        search_paths = [
            _INTERNOS / skill_name,
            _INTERNOS / "vertical_meta_ads" / skill_name,
        ]
        for skill_dir in search_paths:
            skill_py = skill_dir / "skill.py"
            if skill_py.exists():
                return self._import_from_path(skill_name, skill_py, skill_dir)
        return None

    def _import_from_path(self, skill_name: str, skill_py: Path, skill_dir: Path):
        svc_py   = skill_dir / "service.py"
        svc_key  = f"_qa_svc_{skill_name}"
        skill_key = f"_qa_skill_{skill_name}"
        try:
            # Cargar service.py con nombre único para evitar conflicto con 'service' en sys.modules
            if svc_py.exists():
                svc_spec = importlib.util.spec_from_file_location(svc_key, svc_py)
                svc_mod  = importlib.util.module_from_spec(svc_spec)
                sys.modules[svc_key] = svc_mod
                sys.modules["service"] = svc_mod   # alias para que skill.py lo encuentre
                svc_spec.loader.exec_module(svc_mod)

            spec   = importlib.util.spec_from_file_location(skill_key, skill_py)
            module = importlib.util.module_from_spec(spec)
            sys.modules[skill_key] = module
            spec.loader.exec_module(module)
            return module
        except Exception:
            return None
        finally:
            # Limpiar el alias global de 'service' para no contaminar el siguiente skill
            if sys.modules.get("service") is sys.modules.get(svc_key):
                sys.modules.pop("service", None)

    def _run_test(self, module, skill_name: str, suite: dict, verbose: bool) -> dict:
        test_name  = suite["name"]
        ctx        = suite["context"]
        expect_ok  = suite.get("expect_ok")
        expect_keys = suite.get("expect_keys")

        if module is None:
            return {
                "test":    test_name,
                "status":  "fail",
                "semaforo": _SEMAFORO["fail"],
                "message": f"No se pudo cargar {skill_name}/skill.py",
            }

        try:
            result = module.run(ctx)
        except Exception as exc:
            return {
                "test":    test_name,
                "status":  "fail",
                "semaforo": _SEMAFORO["fail"],
                "message": f"Excepción: {exc}",
                **({"traceback": traceback.format_exc()} if verbose else {}),
            }

        # Validar resultado
        if not isinstance(result, dict):
            return {
                "test":    test_name,
                "status":  "fail",
                "semaforo": _SEMAFORO["fail"],
                "message": f"Retorno no es dict: {type(result).__name__}",
            }

        status_ok = True
        reasons   = []

        if expect_ok is not None:
            actual_ok = bool(result.get("ok"))
            if actual_ok != expect_ok:
                status_ok = False
                reasons.append(
                    f"ok={actual_ok} pero se esperaba ok={expect_ok}"
                    f" — error: {result.get('error', '')}"
                )

        if expect_keys:
            data = result.get("data", {})
            for k in expect_keys:
                if k not in data:
                    status_ok = False
                    reasons.append(f"falta clave '{k}' en data")

        return {
            "test":    test_name,
            "status":  "pass" if status_ok else "fail",
            "semaforo": _SEMAFORO["pass" if status_ok else "fail"],
            "message":  "; ".join(reasons) if reasons else "OK",
            **({"result": result} if verbose else {}),
        }
