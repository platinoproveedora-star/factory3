from __future__ import annotations

import importlib.util
from pathlib import Path


def _common():
    path = Path(__file__).resolve().parents[1] / "_common.py"
    spec = importlib.util.spec_from_file_location("multi_shopper_common", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PurchaseQuoteGeneratorSkillService:
    def ejecutar(self, context: dict) -> dict:
        common = _common()
        if context.get("action") == "generate_message":
            return {"ok": True, "data": {"message_body": common.purchase_quote_message(context)}}
        if context.get("action") == "create":
            context = {**context}
            context.setdefault("message_body", common.purchase_quote_message(context))
            context.setdefault("status", "ready_to_send")
        return common.MultiShopperCrudService("purchase_quotes").ejecutar(context)
