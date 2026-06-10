from __future__ import annotations

import importlib.util
from pathlib import Path


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser dict"}
    path = Path(__file__).parent / "service.py"
    spec = importlib.util.spec_from_file_location("erp_billing_dashboard_data_svc", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.ErpBillingDashboardDataService().ejecutar(context)
