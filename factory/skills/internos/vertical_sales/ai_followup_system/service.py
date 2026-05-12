"""Genera mensaje de seguimiento con IA y crea tarea en followup_tasks."""
from __future__ import annotations
import json, os, urllib.request
from datetime import date, timedelta

_SCHEMA = "sales"

_PLANTILLAS = {
    "consulta_comercial": "Hola {nombre}, gracias por contactarnos. ¿En qué puedo ayudarte hoy?",
    "solicitud_precio":   "Hola {nombre}, con gusto te comparto nuestra información de precios. ¿Tienes algún requerimiento específico?",
    "disponibilidad":     "Hola {nombre}, revisamos disponibilidad para ti. ¿Tienes fecha preferida?",
    "agendar_cita":       "Hola {nombre}, con gusto agendamos una cita. ¿Qué días y horarios te funcionan mejor?",
    "seguimiento":        "Hola {nombre}, ¿cómo va tu decisión? Estamos aquí para ayudarte.",
    "queja":              "Hola {nombre}, lamentamos lo sucedido. ¿Me cuentas más para ayudarte de inmediato?",
    "otro":               "Hola {nombre}, gracias por escribirnos. ¿En qué podemos ayudarte?",
}


class AiFollowupService:

    def ejecutar(self, context: dict) -> dict:
        lead_id    = context.get("lead_id", "").strip()
        empresa_id = context.get("empresa_id", "").strip()
        intent     = context.get("intent", "otro").strip()
        nombre     = context.get("nombre") or "cliente"
        historial  = context.get("historial") or []
        dry_run    = context.get("dry_run", True)

        if not lead_id:
            return {"ok": False, "error": "lead_id requerido"}
        if not empresa_id:
            return {"ok": False, "error": "empresa_id requerido"}

        mensaje           = self._generar(intent, nombre, historial)
        fecha_seguimiento = (date.today() + timedelta(days=1)).isoformat()

        if dry_run:
            return {"ok": True, "data": {
                "mensaje_sugerido":  mensaje,
                "fecha_seguimiento": fecha_seguimiento,
                "estado_tarea":      "pendiente",
                "dry_run":           True,
            }}

        url = os.getenv("SUPABASE_URL", "").rstrip("/")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        if not url or not key:
            return {"ok": False, "error": "Faltan SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY"}

        folio = self._next_folio("TASK", url, key)
        saved = self._insert("followup_tasks", {
            "folio":              folio,
            "empresa_id":         empresa_id,
            "lead_id":            lead_id,
            "mensaje_sugerido":   mensaje,
            "fecha_seguimiento":  fecha_seguimiento,
            "estado":             "pendiente",
        }, url, key)
        if not saved.get("ok"):
            return saved

        return {"ok": True, "data": {
            "folio":              folio,
            "mensaje_sugerido":   mensaje,
            "fecha_seguimiento":  fecha_seguimiento,
            "estado_tarea":       "pendiente",
        }}

    def _generar(self, intent: str, nombre: str, historial: list) -> str:
        plantilla = _PLANTILLAS.get(intent, _PLANTILLAS["otro"]).format(nombre=nombre)
        api_key   = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            return plantilla
        hist_txt = ""
        if historial:
            hist_txt = "\nHistorial:\n" + "\n".join(f"- {m}" for m in historial[-3:])
        try:
            prompt = (
                f"Genera un mensaje de seguimiento para lead con intención '{intent}'.\n"
                f"Nombre: {nombre}{hist_txt}\n"
                f"Base: {plantilla}\n\n"
                f"Mejora el mensaje: cálido, personalizado, máximo 2 oraciones.\n"
                f'Responde SOLO con JSON: {{"mensaje": "<texto>"}}'
            )
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=json.dumps({
                    "model":      "claude-haiku-4-5-20251001",
                    "max_tokens": 200,
                    "messages":   [{"role": "user", "content": prompt}],
                }).encode(),
                headers={
                    "content-type":      "application/json",
                    "x-api-key":         api_key,
                    "anthropic-version": "2023-06-01",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as r:
                text = json.loads(r.read().decode())["content"][0]["text"].strip()
                return json.loads(text).get("mensaje", plantilla)
        except Exception:
            return plantilla

    def _next_folio(self, prefix: str, url: str, key: str) -> str:
        try:
            req = urllib.request.Request(
                f"{url}/rest/v1/followup_tasks?select=folio&order=created_at.desc&limit=1",
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
