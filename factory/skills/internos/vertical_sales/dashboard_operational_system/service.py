"""kind=data — retorna leads, tareas y métricas de ventas para dashboard."""
from __future__ import annotations
import json, os, urllib.request

_SCHEMA = "sales"


class DashboardOperationalService:

    def ejecutar(self, context: dict) -> dict:
        empresa_id = context.get("empresa_id", "").strip()
        estado     = context.get("estado", "")
        limit      = int(context.get("limit", 50))

        if not empresa_id:
            return {"ok": False, "error": "empresa_id requerido"}

        url = os.getenv("SUPABASE_URL", "").rstrip("/")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        if not url or not key:
            return {"ok": False, "error": "Faltan SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY"}

        leads   = self._get_leads(empresa_id, estado, limit, url, key)
        tasks   = self._get_tasks(empresa_id, limit, url, key)
        metrics = self._metrics(leads)

        return {"ok": True, "data": {
            "dashboard_leads":   leads,
            "dashboard_tasks":   tasks,
            "dashboard_metrics": metrics,
        }}

    def _get_leads(self, empresa_id: str, estado: str, limit: int, url: str, key: str) -> list:
        try:
            qs = f"empresa_id=eq.{empresa_id}&order=created_at.desc&limit={limit}"
            if estado:
                qs += f"&estado=eq.{estado}"
            req = urllib.request.Request(
                f"{url}/rest/v1/leads?{qs}&select=id,folio,nombre,canal,estado,fuente,score,created_at",
                headers={"apikey": key, "Authorization": f"Bearer {key}", "Accept-Profile": _SCHEMA},
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                return json.loads(r.read().decode())
        except Exception:
            return []

    def _get_tasks(self, empresa_id: str, limit: int, url: str, key: str) -> list:
        try:
            qs = f"empresa_id=eq.{empresa_id}&estado=eq.pendiente&order=fecha_seguimiento.asc&limit={limit}"
            req = urllib.request.Request(
                f"{url}/rest/v1/followup_tasks?{qs}&select=folio,lead_id,mensaje_sugerido,fecha_seguimiento,estado",
                headers={"apikey": key, "Authorization": f"Bearer {key}", "Accept-Profile": _SCHEMA},
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                return json.loads(r.read().decode())
        except Exception:
            return []

    def _metrics(self, leads: list) -> dict:
        total = len(leads)
        por_estado: dict = {}
        total_score = 0
        calientes = 0
        for lead in leads:
            est = lead.get("estado", "desconocido")
            por_estado[est] = por_estado.get(est, 0) + 1
            s = lead.get("score") or 0
            total_score += s
            if s >= 70:
                calientes += 1
        return {
            "total_leads":     total,
            "por_estado":      por_estado,
            "score_promedio":  round(total_score / total, 1) if total else 0,
            "leads_calientes": calientes,
        }
