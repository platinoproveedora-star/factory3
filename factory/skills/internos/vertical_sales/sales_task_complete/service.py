"""Marca tarea de seguimiento como completada o la reprograma con nueva fecha."""
from __future__ import annotations
import json, os, urllib.request
from datetime import datetime, timezone

_SCHEMA   = "sales"
_ACCIONES = {"completar", "reprogramar", "cancelar"}


class SalesTaskCompleteService:

    def ejecutar(self, context: dict) -> dict:
        folio      = context.get("folio", "").strip()
        empresa_id = context.get("empresa_id", "").strip()
        accion     = context.get("accion", "completar").strip()
        nueva_fecha = context.get("nueva_fecha", "")
        dry_run    = context.get("dry_run", True)

        if not folio:
            return {"ok": False, "error": "folio requerido (ej. TASK-001)"}
        if not empresa_id:
            return {"ok": False, "error": "empresa_id requerido"}
        if accion not in _ACCIONES:
            return {"ok": False, "error": f"accion inválida — válidas: {', '.join(_ACCIONES)}"}
        if accion == "reprogramar" and not nueva_fecha:
            return {"ok": False, "error": "nueva_fecha requerida para accion=reprogramar (YYYY-MM-DD)"}

        estado_map = {"completar": "completado", "reprogramar": "pendiente", "cancelar": "cancelado"}
        updates: dict = {
            "estado":     estado_map[accion],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if accion == "reprogramar":
            updates["fecha_seguimiento"] = nueva_fecha

        if dry_run:
            return {"ok": True, "data": {"folio": folio, "accion": accion, "updates": updates, "dry_run": True}}

        url = os.getenv("SUPABASE_URL", "").rstrip("/")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        if not url or not key:
            return {"ok": False, "error": "Faltan SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY"}

        try:
            req = urllib.request.Request(
                f"{url}/rest/v1/followup_tasks?folio=eq.{folio}&empresa_id=eq.{empresa_id}",
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
                    return {"ok": False, "error": "folio no encontrado o empresa_id no coincide"}
                return {"ok": True, "data": {"folio": folio, "accion": accion, "estado": updates["estado"]}}
        except Exception as e:
            return {"ok": False, "error": str(e)}
