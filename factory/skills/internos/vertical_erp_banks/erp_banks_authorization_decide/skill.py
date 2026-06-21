from __future__ import annotations

import importlib.util
from pathlib import Path


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser dict"}
    p = Path(__file__).with_name("service.py")
    spec = importlib.util.spec_from_file_location("erp_banks_authorization_decide_service", p)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module.ErpBanksAuthorizationDecideService().ejecutar(context)
