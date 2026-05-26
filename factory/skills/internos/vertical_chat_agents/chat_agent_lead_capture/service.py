"""Lead capture — extrae campos con Haiku y guarda directo en Supabase."""
from __future__ import annotations

import json
import os
import time
import urllib.request
from pathlib import Path

_ROOT          = Path(__file__).parent.parent.parent.parent.parent.parent
_HAIKU_MODEL   = "claude-haiku-4-5-20251001"
_ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"


class ChatAgentLeadCaptureService:

    def ejecutar(self, context: dict) -> dict:
        text     = self._conversation_text(context)
        user_id  = str(context.get("user_id") or context.get("chat_id") or "").strip()
        canal    = context.get("canal") or "telegram"
        dry_run  = context.get("dry_run", True)
        required = context.get("required_fields") or ["nombre", "telefono", "email"]
        # Schema dinámico: context["schema"] > derivado de company_id > default estoikolab
        company_id = context.get("company_id", "EMP_ESTOIKOLAB")
        schema = context.get("schema") or company_id.replace("EMP_", "").lower()

        if not user_id:
            return {"ok": False, "error": "user_id/chat_id requerido"}

        # Extraer campos con Haiku (entiende lenguaje natural)
        contact = self._extract_with_haiku(text, required)
        missing = [f for f in required if not contact.get(f)]

        if missing:
            return {"ok": True, "data": {
                "saved":         False,
                "contact":       contact,
                "missing_fields": missing,
            }}

        if dry_run:
            return {"ok": True, "data": {
                "saved":   True,
                "contact": contact,
                "lead":    {"folio": "LEAD-DRY", "dry_run": True},
            }}

        # Guardar directo en Supabase
        folio = self._next_folio(schema)
        saved = self._save_supabase(folio, user_id, canal, contact, context, schema)

        return {"ok": True, "data": {
            "saved":   saved,
            "contact": contact,
            "lead":    {"folio": folio, "lead_id": folio},
        }}

    # ── helpers ───────────────────────────────────────────────────────────────

    def _conversation_text(self, context: dict) -> str:
        parts = []
        for item in context.get("history") or []:
            if item.get("role") == "user" and item.get("content"):
                parts.append(str(item["content"]))
        for key in ("message", "text"):
            if context.get(key):
                parts.append(str(context[key]))
        return "\n".join(parts)

    def _extract_with_haiku(self, text: str, required: list) -> dict:
        """Usa Haiku para extraer campos de contacto del texto en lenguaje natural."""
        prompt = (
            "Extrae del siguiente texto estos campos de contacto: nombre, telefono, email.\n"
            "Responde SOLO con JSON válido. Si un campo no aparece, pon null.\n"
            'Ejemplo: {"nombre": "Juan García", "telefono": "5512345678", "email": "juan@empresa.com"}\n\n'
            f"Texto:\n{text}"
        )
        payload = {
            "model":      _HAIKU_MODEL,
            "max_tokens": 256,
            "messages":   [{"role": "user", "content": prompt}],
        }
        try:
            req = urllib.request.Request(
                _ANTHROPIC_URL,
                data=json.dumps(payload).encode(),
                headers={
                    "content-type":      "application/json",
                    "x-api-key":         os.getenv("ANTHROPIC_API_KEY", ""),
                    "anthropic-version": "2023-06-01",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as r:
                body     = json.loads(r.read().decode())
                raw      = body["content"][0]["text"].strip()
                # Limpiar posibles backticks de markdown
                raw      = raw.strip("`").strip()
                if raw.startswith("json"):
                    raw = raw[4:].strip()
                extracted = json.loads(raw)
                return {k: (v or "") for k, v in extracted.items()}
        except Exception:
            return {}

    def _next_folio(self, schema: str) -> str:
        try:
            url = f"{os.getenv('SUPABASE_URL')}/rest/v1/chat_leads?select=id"
            req = urllib.request.Request(url, headers={
                "apikey":         os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
                "Authorization":  f"Bearer {os.getenv('SUPABASE_SERVICE_ROLE_KEY', '')}",
                "Accept-Profile": schema,
            })
            with urllib.request.urlopen(req, timeout=10) as r:
                rows = json.loads(r.read().decode())
                return f"LEAD-{len(rows) + 1:03d}"
        except Exception:
            return f"LEAD-{int(time.time()) % 100000:05d}"

    def _save_supabase(self, folio: str, user_id: str, canal: str, contact: dict, context: dict, schema: str) -> bool:
        row = {
            "folio":        folio,
            "agent_id":     context.get("agent_id", "AGT-001"),
            "canal":        canal,
            "user_id":      user_id,
            "nombre":       contact.get("nombre"),
            "telefono":     contact.get("telefono"),
            "email":        contact.get("email"),
            "empresa":      contact.get("empresa"),
            "tipo_negocio": contact.get("tipo_de_negocio"),
            "objetivo":     contact.get("objetivo"),
            "status":       "nuevo",
        }
        try:
            data = json.dumps(row).encode()
            req  = urllib.request.Request(
                f"{os.getenv('SUPABASE_URL')}/rest/v1/chat_leads",
                data=data,
                headers={
                    "apikey":          os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
                    "Authorization":   f"Bearer {os.getenv('SUPABASE_SERVICE_ROLE_KEY', '')}",
                    "Content-Type":    "application/json",
                    "Content-Profile": schema,
                    "Prefer":          "return=minimal",
                },
                method="POST",
            )
            urllib.request.urlopen(req, timeout=10)
            return True
        except Exception:
            return False
