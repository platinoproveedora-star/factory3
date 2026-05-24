def render(model: str = "claude-haiku-4-5-20251001") -> str:
    return f'''"""Anthropic brain for this Factory agent."""

from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path
from typing import Any

MODEL = "{model}"
ANTHROPIC_VERSION = "2023-06-01"


def respond(message: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    if not isinstance(message, str) or not message.strip():
        return {{"ok": False, "error": "message debe ser texto no vacio"}}

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return {{"ok": False, "error": "ANTHROPIC_API_KEY no configurada"}}

    system_prompt = _build_system_prompt(context or {{}})
    payload = {{
        "model": MODEL,
        "max_tokens": 800,
        "system": system_prompt,
        "messages": [{{"role": "user", "content": message}}],
    }}
    if context:
        payload["metadata"] = {{"user_id": str(context.get("user_id", ""))[:64]}}

    request = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(payload).encode("utf-8"),
        headers={{
            "content-type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": ANTHROPIC_VERSION,
        }},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        return {{"ok": False, "error": str(exc)}}

    text = _extract_text(data)
    return {{"ok": True, "response": text, "model": MODEL, "provider": "anthropic"}}


def _read_system_prompt() -> str:
    prompt_path = Path(__file__).resolve().parent / "prompts" / "system.md"
    if not prompt_path.exists():
        return "Eres un agente de Factory. Responde de forma clara, breve y util."
    return prompt_path.read_text(encoding="utf-8", errors="replace").strip()


def _build_system_prompt(context: dict[str, Any]) -> str:
    system_prompt = _read_system_prompt()
    memories = context.get("memories", [])
    if not isinstance(memories, list) or not memories:
        return system_prompt

    lines = []
    for item in memories[:8]:
        if isinstance(item, dict):
            content = str(item.get("content", "")).strip()
        else:
            content = str(item).strip()
        if content:
            lines.append(f"- {{content}}")
    if not lines:
        return system_prompt

    memory_block = "\\n".join(lines)
    return f"{{system_prompt}}\\n\\nMemoria relevante del usuario:\\n{{memory_block}}"


def _extract_text(data: dict[str, Any]) -> str:
    parts = []
    for item in data.get("content", []):
        if isinstance(item, dict) and item.get("type") == "text":
            parts.append(item.get("text", ""))
    text = "\\n".join(part for part in parts if part).strip()
    return text or "No pude generar respuesta."
'''
