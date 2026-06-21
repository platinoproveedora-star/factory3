from __future__ import annotations

import importlib.util
from pathlib import Path

p = Path(__file__).with_name("service.py")
spec = importlib.util.spec_from_file_location("erp_banks_expense_reconcile_service", p)
mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(mod)


def run(context: dict) -> dict:
    return mod.ErpBanksExpenseReconcileService().ejecutar(context)
