"""Guarda historial de mensajes (in/out) por lead en conversation_messages."""
from __future__ import annotations
import json, os, urllib.request

_SCHEMA      = "sales"
_DIRECCIONES = {"in", "out"}


class ConversationLogService:

    def ejecutar(self, context: dict) -> dict:
        lead_id    = context.get("lead_id", "").strip()
        empresa_id = context.get("empresa_id", "").strip()
        canal      = context.get("canal", "telegram").strip()
        direccion  = context.get("direccion", "in").strip()
        texto      = context.get("texto", "").strip()
        dry_run    = context.get("dry_run", True)

        if not lead_id:
            return {"ok": False, "error": "lead_id requerido"}
        if not empresa_id:
            return {"ok": False, "error": "empresa_id requerido"}
        if not texto:
            return {"ok": False, "error": "texto requerido"}
        if direccion not in _DIRECCIONES:
            return {"ok": False, "error": f"direccion inválida — válidas: in, out"}

        if dry_run:
            return {"ok": True, "data": {"folio": "MSG-DRY", "lead_id": lead_id, "dry_run": True}}

        url = os.getenv("SUPABASE_URL", "").rstrip("/")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        if not url or not key:
            return {"ok": False, "error": "Faltan SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY"}

        folio = self._next_folio("MSG", url, key)
        saved = self._insert("conversation_messages", {
            "folio":      folio,
            "empresa_id": empresa_id,
            "lead_id":    lead_id,
            "canal":      canal,
            "direccion":  direccion,
            "texto":      texto,
        }, url, key)
        if not saved.get("ok"):
            return saved

        return {"ok": True, "data": {"folio": folio, "lead_id": lead_id}}

    def _next_folio(self, prefix: str, url: str, key: str) -> str:
        try:
            req = urllib.request.Request(
                f"{url}/rest/v1/conversation_messages?select=folio&order=created_at.desc&limit=1",
                headers={"apikey": key, "Authorization": f"Bearer {key}", "Accept-Profile": _SCHEMA},
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                rows = json.loads(r.read().decode())
                if rows:
                    return f"{prefix}-{int(rows[0]['folio'].split('-')[-1]) + 1:03d}"
        except Exception:
            pass
        return f"{prefix}-001"

    def _insert(self, table: str, row: dict, url: str, key: str) -> dict:
        try:
            req = urllib.request.Request(
                f"{url}/rest/v1/{table}",
                data=json.dumps(row).encode(),
                headers={
                    "apikey":          key,
                    "Authorization":   f"Bearer {key}",
                    "Content-Type":    "application/json",
                    "Content-Profile": _SCHEMA,
                    "Prefer":          "return=representation",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                rows = json.loads(r.read().decode())
                return {"ok": True, "data": rows[0] if rows else row}
        except Exception as e:
            return {"ok": False, "error": str(e)}
