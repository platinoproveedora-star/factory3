"""Lead capture bridge from chat agents to vertical_sales."""
from __future__ import annotations

import re
from pathlib import Path


_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent


class ChatAgentLeadCaptureService:
    def ejecutar(self, context: dict) -> dict:
        text = self._conversation_text(context)
        empresa_id = context.get("empresa_id") or context.get("company_id") or "EMP_ESTOIKOLAB"
        user_id = str(context.get("user_id") or context.get("chat_id") or "").strip()
        canal = context.get("canal") or "telegram"
        dry_run = context.get("dry_run", True)
        required = context.get("required_fields") or ["nombre", "telefono", "email"]

        if not user_id:
            return {"ok": False, "error": "user_id/chat_id requerido"}

        contact = self._extract(text, context)
        missing = [field for field in required if not contact.get(field)]
        if missing:
            return {
                "ok": True,
                "data": {
                    "saved": False,
                    "contact": contact,
                    "missing_fields": missing,
                    "message": "faltan datos requeridos",
                },
            }

        intent = context.get("intent") or "consulta_comercial"
        if dry_run:
            return {
                "ok": True,
                "data": {
                    "saved": True,
                    "contact": contact,
                    "lead": {"dry_run": True},
                    "intent": intent,
                },
            }

        from factory.engine import SkillLoader, SkillRunner

        loader = SkillLoader(
            internal_root=_ROOT / "factory" / "skills" / "internos",
            external_root=_ROOT / "factory" / "skills" / "externos",
        )
        runner = SkillRunner(loader)
        lead = runner.run(
            "vertical_sales/lead_pipeline_system",
            {
                "empresa_id": empresa_id,
                "canal": canal,
                "user_id": user_id,
                "intent": intent,
                "texto": text,
                "nombre": contact.get("nombre", ""),
                "telefono": contact.get("telefono", ""),
                "email": contact.get("email", ""),
                "force_new": bool(context.get("force_new", False)),
                "dry_run": False,
            },
            source="internos",
        )
        return {
            "ok": lead.get("ok", False),
            "data": {
                "saved": lead.get("ok", False),
                "contact": contact,
                "lead": lead.get("data"),
            },
            "error": lead.get("error"),
        }

    def _conversation_text(self, context: dict) -> str:
        parts = []
        for item in context.get("history") or []:
            if item.get("role") == "user" and item.get("content"):
                parts.append(str(item["content"]))
        for key in ("text", "message"):
            if context.get(key):
                parts.append(str(context[key]))
        return "\n".join(parts)

    def _extract(self, text: str, context: dict) -> dict:
        email_match = re.search(r"[\w.\-+]+@[\w.\-]+\.\w+", text)
        phone_match = re.search(r"(?:\+?\d[\d\s().-]{7,}\d)", text)
        name = context.get("nombre") or context.get("name") or ""

        if not name:
            match = re.search(
                r"(?:soy|me llamo|mi nombre es)\s+([A-Za-zÁÉÍÓÚáéíóúÑñ ]{2,50})",
                text,
                re.I,
            )
            if match:
                name = match.group(1).strip()

        if not name:
            cleaned = text
            if email_match:
                cleaned = cleaned.replace(email_match.group(0), " ")
            if phone_match:
                cleaned = cleaned.replace(phone_match.group(0), " ")
            first = re.split(r"[,;\n]", cleaned.strip())[0].strip()
            first = re.sub(r"^(hola|buenas|buen dia|soy)\s+", "", first, flags=re.I).strip()
            if first and len(first.split()) <= 5 and not any(ch.isdigit() for ch in first):
                name = first

        return {
            "nombre": name,
            "email": email_match.group(0) if email_match else context.get("email", ""),
            "telefono": phone_match.group(0).strip() if phone_match else context.get("telefono", ""),
            "raw_text": text,
        }
