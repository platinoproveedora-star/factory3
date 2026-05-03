"""Service for memory_summarizer - compact rule-based memory summaries."""

from __future__ import annotations


class MemorySummarizerService:

    def ejecutar(self, context: dict) -> dict:
        memories = context.get("memories", context.get("items", []))
        if isinstance(memories, str):
            memories = [line.strip() for line in memories.splitlines() if line.strip()]
        if not isinstance(memories, list):
            return {"ok": False, "error": "memories debe ser lista o texto multilinea"}
        limit = context.get("limit", 8)
        if not isinstance(limit, int) or limit < 1:
            return {"ok": False, "error": "limit debe ser entero positivo"}
        bullets = []
        seen = set()
        for item in memories:
            text = self._content(item)
            if not text:
                continue
            key = text.lower()
            if key in seen:
                continue
            seen.add(key)
            bullets.append(f"- {text[:180]}")
            if len(bullets) >= limit:
                break
        return {"ok": True, "data": {"summary": "\n".join(bullets), "count": len(bullets)}}

    def _content(self, item: object) -> str:
        if isinstance(item, dict):
            return str(item.get("content") or item.get("text") or "").strip()
        return str(item).strip()
