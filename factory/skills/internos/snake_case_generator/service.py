"""Service for snake_case_generator - creates valid identifiers."""

from __future__ import annotations

import re
import unicodedata


class SnakeCaseGeneratorService:

    def ejecutar(self, context: dict) -> dict:
        text = context.get("text", context.get("name", ""))
        if not isinstance(text, str):
            return {"ok": False, "error": "text debe ser texto"}
        value = self._slug(text)
        if context.get("allow_dash"):
            value = value.replace("_", "-")
        if not value:
            return {"ok": False, "error": "no se pudo generar identificador"}
        return {"ok": True, "data": {"value": value}}

    def _slug(self, text: str) -> str:
        normalized = "".join(
            char for char in unicodedata.normalize("NFD", text.lower())
            if unicodedata.category(char) != "Mn"
        )
        normalized = re.sub(r"[^a-z0-9]+", "_", normalized).strip("_")
        normalized = re.sub(r"_+", "_", normalized)
        if normalized and normalized[0].isdigit():
            normalized = f"n_{normalized}"
        return normalized
