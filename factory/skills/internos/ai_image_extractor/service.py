"""Generic AI document/image extractor using Claude Haiku."""

from __future__ import annotations

import json
import os
import urllib.request


class AiImageExtractorService:

    def ejecutar(self, context: dict) -> dict:
        content_b64 = context.get("content_base64", "")
        media_type  = context.get("media_type", "image/jpeg")
        schema      = context.get("schema", {})
        ctx         = context.get("context", "")

        if not content_b64:
            return {"ok": False, "error": "content_base64 requerido"}
        if not schema:
            return {"ok": False, "error": "schema requerido"}

        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            return {"ok": False, "error": "ANTHROPIC_API_KEY no configurada"}

        schema_str  = json.dumps(schema, ensure_ascii=False, indent=2)
        instruction = (
            (f"{ctx}\n\n" if ctx else "") +
            f"Extrae los datos y devuelve SOLO un JSON con exactamente estos campos:\n{schema_str}\n"
            "Si un campo no se puede determinar usa null. No incluyas texto fuera del JSON."
        )

        if media_type == "text/plain":
            import base64
            text     = base64.b64decode(content_b64).decode("utf-8", errors="replace")
            messages = [{"role": "user", "content": f"{instruction}\n\nTexto:\n{text}"}]
        elif media_type == "application/pdf":
            messages = [{"role": "user", "content": [
                {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": content_b64}},
                {"type": "text", "text": instruction},
            ]}]
        else:
            messages = [{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": content_b64}},
                {"type": "text", "text": instruction},
            ]}]

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
            text  = "".join(
                item.get("text", "") for item in result.get("content", []) if item.get("type") == "text"
            ).strip()
            start = text.find("{")
            end   = text.rfind("}") + 1
            if start >= 0 and end > start:
                return {"ok": True, "data": {"extracted": json.loads(text[start:end])}}
            return {"ok": False, "error": "Sin JSON en respuesta", "data": {"raw": text}}
        except Exception as e:
            return {"ok": False, "error": str(e)}
