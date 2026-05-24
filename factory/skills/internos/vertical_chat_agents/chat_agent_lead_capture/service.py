"""Lead capture bridge from chat agents to vertical_sales."""
from __future__ import annotations
import re
from pathlib import Path


_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent


class ChatAgentLeadCaptureService:
    def ejecutar(self, context: dict) -> dict:
        text = context.get("text") or context.get("message") or ""
        empresa_id = context.get("empresa_id") or context.get("company_id") or "EMP_ESTOIKOLAB"
        user_id = str(context.get("user_id") or context.get("chat_id") or "").strip()
        canal = context.get("canal") or "telegram"
        dry_run = context.get("dry_run", True)
        if not user_id:
            return {"ok": False, "error": "user_id/chat_id requerido"}
        contact = self._extract(text, context)
        intent = context.get("intent") or "consulta_comercial"
        if dry_run:
            return {"ok": True, "data": {"contact": contact, "lead": {"dry_run": True}, "intent": intent}}

        from factory.engine import SkillLoader, SkillRunner
        loader = SkillLoader(internal_root=_ROOT / "factory" / "skills" / "internos", external_root=_ROOT / "factory" / "skills" / "externos")
        runner = SkillRunner(loader)
        lead = runner.run("vertical_sales/lead_pipeline_system", {
            "empresa_id": empresa_id,
            "canal": canal,
            "user_id": user_id,
            "intent": intent,
            "texto": text,
            "nombre": contact.get("nombre", ""),
            "telefono": contact.get("telefono", ""),
            "email": contact.get("email", ""),
            "dry_run": False
        }, source="internos")
        return {"ok": lead.get("ok", False), "data": {"contact": contact, "lead": lead.get("data")}, "error": lead.get("error")}

    def _extract(self, text: str, context: dict) -> dict:
        email_match = re.search(r"[\w.\-+]+@[\w.\-]+\.\w+", text)
        phone_match = re.search(r"(?:\+?\d[\d\s().-]{7,}\d)", text)
        name = context.get("nombre") or context.get("name") or ""
        if not name:
            m = re.search(r"(?:soy|me llamo|mi nombre es)\s+([A-Za-zÁÉÍÓÚáéíóúÑñ ]{2,40})", text, re.I)
            if m:
                name = m.group(1).strip()
        return {
            "nombre": name,
            "email": email_match.group(0) if email_match else context.get("email", ""),
            "telefono": phone_match.group(0).strip() if phone_match else context.get("telefono", ""),
            "raw_text": text
        }
