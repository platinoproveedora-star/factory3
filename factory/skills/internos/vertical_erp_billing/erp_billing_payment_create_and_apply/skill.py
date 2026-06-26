from __future__ import annotations

import importlib.util
from pathlib import Path


def run(context: dict) -> dict:
    path = Path(__file__).with_name("service.py")
    spec = importlib.util.spec_from_file_location("erp_billing_payment_create_and_apply_service", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module.ErpBillingPaymentCreateAndApplyService().ejecutar(context)
