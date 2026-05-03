"""Service for text_cleaner - normalizes plain text."""

from __future__ import annotations

import re
import unicodedata


class TextCleanerService:

    def ejecutar(self, context: dict) -> dict:
        text = context.get("text", "")
        if not isinstance(text, str):
            return {"ok": False, "error": "text debe ser texto"}
        result = text.replace("\r\n", "\n").replace("\r", "\n")
        if context.get("trim", True):
            result = "\n".join(line.strip() for line in result.splitlines())
        if context.get("collapse_spaces", True):
            result = re.sub(r"[ \t]+", " ", result)
        if context.get("collapse_blank_lines", True):
            result = re.sub(r"\n{3,}", "\n\n", result)
        if context.get("lower"):
            result = result.lower()
        if context.get("upper"):
            result = result.upper()
        if context.get("remove_accents"):
            result = "".join(
                char for char in unicodedata.normalize("NFD", result)
                if unicodedata.category(char) != "Mn"
            )
        return {"ok": True, "data": {"text": result}}
