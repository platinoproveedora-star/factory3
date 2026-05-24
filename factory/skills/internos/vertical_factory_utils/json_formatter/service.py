"""Service for json_formatter - validates and formats JSON."""

from __future__ import annotations

import json


class JsonFormatterService:

    def ejecutar(self, context: dict) -> dict:
        value = context.get("json", context.get("text"))
        indent = context.get("indent", 2)
        if not isinstance(indent, int) or indent < 0:
            return {"ok": False, "error": "indent debe ser entero no negativo"}
        try:
            data = json.loads(value) if isinstance(value, str) else value
        except json.JSONDecodeError as exc:
            return {"ok": False, "error": f"JSON invalido: {exc.msg}", "data": {"line": exc.lineno, "column": exc.colno}}
        try:
            formatted = json.dumps(data, indent=indent, ensure_ascii=False, sort_keys=bool(context.get("sort_keys", False)))
        except TypeError as exc:
            return {"ok": False, "error": f"valor no serializable: {exc}"}
        return {"ok": True, "data": {"json": formatted, "parsed": data}}
