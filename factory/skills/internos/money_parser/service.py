"""Service for money_parser - extracts money amounts from text."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

_AMOUNT = re.compile(r"(?i)(?:mxn|usd|\$)?\s*(-?\d[\d,]*(?:\.\d+)?)\s*(?:pesos|mxn|usd|dolares|dólares)?")


class MoneyParserService:

    def ejecutar(self, context: dict) -> dict:
        text = context.get("text", "")
        if not isinstance(text, str):
            return {"ok": False, "error": "text debe ser texto"}
        amounts = []
        for match in _AMOUNT.finditer(text):
            raw = match.group(1)
            try:
                value = Decimal(raw.replace(",", ""))
            except InvalidOperation:
                continue
            amounts.append({"raw": match.group(0).strip(), "amount": float(value)})
        return {"ok": True, "data": {"amounts": amounts, "count": len(amounts)}}
