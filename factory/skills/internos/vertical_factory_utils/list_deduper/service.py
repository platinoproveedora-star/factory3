"""Service for list_deduper - removes duplicates preserving order."""

from __future__ import annotations


class ListDeduperService:

    def ejecutar(self, context: dict) -> dict:
        items = context.get("items", [])
        if isinstance(items, str):
            items = [line for line in items.splitlines() if line.strip()]
        if not isinstance(items, list):
            return {"ok": False, "error": "items debe ser lista o texto multilinea"}
        case_sensitive = bool(context.get("case_sensitive", False))
        seen = set()
        result = []
        for item in items:
            key = str(item) if case_sensitive else str(item).lower()
            if key in seen:
                continue
            seen.add(key)
            result.append(item)
        return {"ok": True, "data": {"items": result, "removed": len(items) - len(result)}}
