"""Service for simple_calculator - safe basic arithmetic."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation


class SimpleCalculatorService:

    def ejecutar(self, context: dict) -> dict:
        operation = str(context.get("operation", "")).lower()
        values = context.get("values", [])
        if not isinstance(values, list) or not values:
            return {"ok": False, "error": "values debe ser lista no vacia"}
        try:
            numbers = [Decimal(str(value)) for value in values]
        except InvalidOperation:
            return {"ok": False, "error": "values debe contener numeros"}
        if operation in {"sum", "suma", "add"}:
            result = sum(numbers, Decimal("0"))
        elif operation in {"subtract", "resta"}:
            result = numbers[0] - sum(numbers[1:], Decimal("0"))
        elif operation in {"multiply", "multiplica"}:
            result = Decimal("1")
            for number in numbers:
                result *= number
        elif operation in {"divide", "division"}:
            result = numbers[0]
            for number in numbers[1:]:
                if number == 0:
                    return {"ok": False, "error": "division entre cero"}
                result /= number
        else:
            return {"ok": False, "error": "operation debe ser sum, subtract, multiply o divide"}
        return {"ok": True, "data": {"result": float(result), "result_text": str(result)}}
