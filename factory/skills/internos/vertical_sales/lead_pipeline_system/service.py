"""Convierte mensaje comercial en lead: dedup, creación con folio VEN-XXX, estado inicial."""
from __future__ import annotations
import json, os, urllib.request

_SCHEMA           = "sales"
_INTENT_COMERCIAL = {"consulta_comercial", "solicitud_precio", "disponibilidad", "agendar_cita", "seguimiento"}


class LeadPipelineService:

    def ejecutar(self, context: dict) -> dict:
        empresa_id = context.get("empresa_id", "").strip()
        canal      = context.get("canal", "telegram").strip()
        user_id    = str(context.get("user_id", "")).strip()
        intent     = context.get("intent", "otro").strip()
        texto      = context.get("texto", "")
        nombre     = context.get("nombre", "")
        telefono   = context.get("telefono", "")
        email      = context.get("email", "")
        dry_run    = context.get("dry_run", True)

        if not empresa_id:
            return {"ok": False, "error": "empresa_id requerido"}
        if not user_id:
            return {"ok": False, "error": "user_id requerido"}

        if intent not in _INTENT_COMERCIAL:
            return {"ok": True, "data": {
                "lead_id":  None,
                "folio":    None,
                "estado":   None,
                "es_nuevo": False,
                "mensaje":  f"intent '{intent}' no es comercial — lead no creado",
            }}

        if dry_run:
            return {"ok": True, "data": {
                "lead_id":  "uuid-dry",
                "folio":    "VEN-DRY",
                "estado":   "nuevo",
                "fuente":   canal,
                "es_nuevo": True,
                "dry_run":  True,
            }}

        url = os.getenv("SUPABASE_URL", "").rstrip("/")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        if not url or not key:
            return {"ok": False, "error": "Faltan SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY"}

        existing = self._find_lead(user_id, canal, empresa_id, url, key)
        if existing:
            return {"ok": True, "data": {
                "lead_id":  existing["id"],
                "folio":    existing["folio"],
                "estado":   existing["estado"],
                "fuente":   existing.get("fuente", canal),
                "es_nuevo": False,
            }}

        folio = self._next_folio("VEN", url, key)
        saved = self._insert("leads", {
            "folio":      folio,
            "empresa_id": empresa_id,
            "canal":      canal,
            "user_id":    user_id,
            "nombre":     nombre or None,
            "telefono":   telefono or None,
            "email":      email or None,
            "estado":     "nuevo",
            "fuente":     canal,
            "score":      0,
        }, url, key)
        if not saved.get("ok"):
            return saved

        lead = saved["data"]
        return {"ok": True, "data": {
            "lead_id":  lead["id"],
            "folio":    lead["folio"],
            "estado":   lead["estado"],
            "fuente":   lead["fuente"],
            "es_nuevo": True,
        }}

    def _find_lead(self, user_id: str, canal: str, empresa_id: str, url: str, key: str) -> dict | None:
        try:
            qs = f"user_id=eq.{user_id}&canal=eq.{canal}&empresa_id=eq.{empresa_id}&limit=1"
            req = urllib.request.Request(
                f"{url}/rest/v1/leads?{qs}&select=id,folio,estado,fuente",
                headers={"apikey": key, "Authorization": f"Bearer {key}", "Accept-Profile": _SCHEMA},
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                rows = json.loads(r.read().decode())
                return rows[0] if rows else None
        except Exception:
            return None

    def _next_folio(self, prefix: str, url: str, key: str) -> str:
        try:
            req = urllib.request.Request(
                f"{url}/rest/v1/leads?select=folio&order=created_at.desc&limit=1",
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
