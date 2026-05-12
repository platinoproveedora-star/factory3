"""Actualiza campos del lead: nombre, teléfono, email, estado. Registra updated_at."""
from __future__ import annotations
import json, os, urllib.request
from datetime import datetime, timezone

_SCHEMA  = "sales"
_ESTADOS = {"nuevo", "contactado", "calificado", "propuesta", "ganado", "perdido"}
_CAMPOS  = {"nombre", "telefono", "email", "estado"}


class SalesLeadUpdateService:

    def ejecutar(self, context: dict) -> dict:
        lead_id    = context.get("lead_id", "").strip()
        empresa_id = context.get("empresa_id", "").strip()
        dry_run    = context.get("dry_run", True)

        if not lead_id:
            return {"ok": False, "error": "lead_id requerido"}
        if not empresa_id:
            return {"ok": False, "error": "empresa_id requerido"}

        updates = {k: context[k] for k in _CAMPOS if k in context and context[k] is not None}
        if not updates:
            return {"ok": False, "error": f"Debe enviarse al menos un campo: {', '.join(_CAMPOS)}"}

        if "estado" in updates and updates["estado"] not in _ESTADOS:
            return {"ok": False, "error": f"estado inválido — válidos: {', '.join(_ESTADOS)}"}

        if dry_run:
            return {"ok": True, "data": {
                "lead_id":  lead_id,
                "updated":  updates,
                "dry_run":  True,
            }}

        url = os.getenv("SUPABASE_URL", "").rstrip("/")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        if not url or not key:
            return {"ok": False, "error": "Faltan SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY"}

        updates["updated_at"] = datetime.now(timezone.utc).isoformat()

        try:
            req = urllib.request.Request(
                f"{url}/rest/v1/leads?id=eq.{lead_id}&empresa_id=eq.{empresa_id}",
                data=json.dumps(updates).encode(),
                headers={
                    "apikey":          key,
                    "Authorization":   f"Bearer {key}",
                    "Content-Type":    "application/json",
                    "Content-Profile": _SCHEMA,
                    "Prefer":          "return=representation",
                },
                method="PATCH",
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                rows = json.loads(r.read().decode())
                if not rows:
                    return {"ok": False, "error": "lead_id no encontrado o empresa_id no coincide"}
                return {"ok": True, "data": {"lead_id": lead_id, "updated": updates}}
        except Exception as e:
            return {"ok": False, "error": str(e)}
