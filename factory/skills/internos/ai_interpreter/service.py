"""Generic AI interpreter using Claude Haiku — extract or classify+extract."""

from __future__ import annotations

import base64
import json
import os
import urllib.request


def run(context: dict) -> dict:
    mode        = context.get("mode", "extract")
    text        = context.get("text", "")
    content_b64 = context.get("content_b64") or context.get("content_base64", "")
    media_type  = context.get("media_type", "text/plain")
    schema      = context.get("schema", {})
    actions     = context.get("actions", {})
    hint        = context.get("hint", "")
    ctx         = context.get("context", "")

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return {"ok": False, "error": "ANTHROPIC_API_KEY no configurada"}

    if mode == "extract":
        if not schema:
            return {"ok": False, "error": "schema requerido para mode=extract"}
        instruction = _extract_instruction(schema, ctx)
    elif mode == "classify":
        if not actions:
            return {"ok": False, "error": "actions requerido para mode=classify"}
        instruction = _classify_instruction(actions, hint, ctx)
    else:
        return {"ok": False, "error": f"mode invalido: {mode}. Usar 'extract' o 'classify'"}

    messages = _build_messages(instruction, text, content_b64, media_type)
    raw = _call_haiku(messages, api_key)
    if not raw.get("ok"):
        return raw

    text_out = raw["text"]
    start = text_out.find("{")
    end   = text_out.rfind("}") + 1
    if start < 0 or end <= start:
        return {"ok": False, "error": "Sin JSON en respuesta", "data": {"raw": text_out}}

    try:
        parsed = json.loads(text_out[start:end])
    except json.JSONDecodeError as e:
        return {"ok": False, "error": f"JSON invalido: {e}", "data": {"raw": text_out}}

    if mode == "extract":
        return {"ok": True, "data": {"extracted": parsed}}
    return {"ok": True, "data": {"action": parsed.get("action", "desconocido"), "fields": parsed.get("data", {})}}


def _extract_instruction(schema: dict, ctx: str) -> str:
    schema_str = json.dumps(schema, ensure_ascii=False, indent=2)
    return (
        (f"{ctx}\n\n" if ctx else "") +
        f"Extrae los datos y devuelve SOLO un JSON con exactamente estos campos:\n{schema_str}\n"
        "Si un campo no se puede determinar usa null. No incluyas texto fuera del JSON."
    )


def _classify_instruction(actions: dict, hint: str, ctx: str) -> str:
    action_names = list(actions.keys())
    actions_desc = []
    for name, schema in actions.items():
        fields = ", ".join(schema.keys()) if schema else ""
        actions_desc.append(f"{name.upper()} → campos: {fields}")

    return (
        (f"PISTA: probablemente es un {hint.upper()}.\n\n" if hint else "") +
        (f"{ctx}\n\n" if ctx else "") +
        f'Analiza la entrada y devuelve SOLO un JSON: {{"action": "{"|".join(action_names + ["desconocido"])}", "data": {{...}}}}\n\n' +
        "\n".join(actions_desc) + "\n\n"
        "Usa null para campos no determinables. No escribas nada fuera del JSON."
    )


def _build_messages(instruction: str, text: str, content_b64: str, media_type: str) -> list:
    if content_b64 and media_type not in ("text/plain", ""):
        if media_type == "application/pdf":
            content = [
                {"type": "document", "source": {"type": "base64", "media_type": media_type, "data": content_b64}},
                {"type": "text",     "text": instruction},
            ]
        else:
            content = [
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": content_b64}},
                {"type": "text",  "text": instruction},
            ]
    else:
        if content_b64 and media_type == "text/plain":
            try:
                text = base64.b64decode(content_b64).decode("utf-8", errors="replace")
            except Exception:
                pass
        content = f"{instruction}\n\nEntrada:\n{text}" if text else instruction

    return [{"role": "user", "content": content}]


def _call_haiku(messages: list, api_key: str) -> dict:
    payload = {"model": "claude-haiku-4-5-20251001", "max_tokens": 1024, "messages": messages}
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(payload).encode(),
        headers={
            "content-type":      "application/json",
            "x-api-key":         api_key,
            "anthropic-version": "2023-06-01",
            "anthropic-beta":    "pdfs-2024-09-25",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode())
        text = "".join(
            item.get("text", "") for item in result.get("content", []) if item.get("type") == "text"
        ).strip()
        return {"ok": True, "text": text}
    except Exception as e:
        return {"ok": False, "error": str(e)}
