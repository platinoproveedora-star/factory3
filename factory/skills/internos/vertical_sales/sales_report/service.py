"""kind=data — reporte de conversión por período: leads, tasa cierre, score promedio, por canal."""
from __future__ import annotations
import json, os, urllib.request
from datetime import datetime, timedelta, timezone

_SCHEMA   = "sales"
_PERIODOS = {"7d": 7, "30d": 30, "90d": 90}


class SalesReportService:

    def ejecutar(self, context: dict) -> dict:
        empresa_id = context.get("empresa_id", "").strip()
        periodo    = context.get("periodo", "30d").strip()
        estado     = context.get("estado", "")

        if not empresa_id:
            return {"ok": False, "error": "empresa_id requerido"}
        if periodo not in _PERIODOS:
            return {"ok": False, "error": f"periodo inválido — válidos: {', '.join(_PERIODOS)}"}

        url = os.getenv("SUPABASE_URL", "").rstrip("/")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        if not url or not key:
            return {"ok": False, "error": "Faltan SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY"}

        dias   = _PERIODOS[periodo]
        desde  = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()
        leads  = self._get_leads(empresa_id, desde, url, key)
        tasks  = self._get_tasks(empresa_id, desde, url, key)

        total  = len(leads)
        ganados = sum(1 for l in leads if l.get("estado") == "ganado")
        perdidos = sum(1 for l in leads if l.get("estado") == "perdido")
        tasa_cierre = round(ganados / total * 100, 1) if total else 0

        por_estado: dict = {}
        por_canal:  dict = {}
        por_nivel:  dict = {"caliente": 0, "tibio": 0, "frio": 0}
        total_score = 0

        for lead in leads:
            est = lead.get("estado", "desconocido")
            por_estado[est] = por_estado.get(est, 0) + 1
            can = lead.get("canal", "desconocido")
            por_canal[can] = por_canal.get(can, 0) + 1
            s = lead.get("score") or 0
            total_score += s
            if s >= 70:
                por_nivel["caliente"] += 1
            elif s >= 40:
                por_nivel["tibio"] += 1
            else:
                por_nivel["frio"] += 1

        tareas_pendientes   = sum(1 for t in tasks if t.get("estado") == "pendiente")
        tareas_completadas  = sum(1 for t in tasks if t.get("estado") == "completado")

        return {"ok": True, "data": {
            "periodo":           periodo,
            "empresa_id":        empresa_id,
            "total_leads":       total,
            "leads_ganados":     ganados,
            "leads_perdidos":    perdidos,
            "tasa_cierre_pct":   tasa_cierre,
            "score_promedio":    round(total_score / total, 1) if total else 0,
            "por_estado":        por_estado,
            "por_canal":         por_canal,
            "por_nivel":         por_nivel,
            "tareas_pendientes": tareas_pendientes,
            "tareas_completadas": tareas_completadas,
        }}

    def _get_leads(self, empresa_id: str, desde: str, url: str, key: str) -> list:
        try:
            qs = f"empresa_id=eq.{empresa_id}&created_at=gte.{desde}&select=estado,canal,score"
            req = urllib.request.Request(
                f"{url}/rest/v1/leads?{qs}",
                headers={"apikey": key, "Authorization": f"Bearer {key}", "Accept-Profile": _SCHEMA},
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                return json.loads(r.read().decode())
        except Exception:
            return []

    def _get_tasks(self, empresa_id: str, desde: str, url: str, key: str) -> list:
        try:
            qs = f"empresa_id=eq.{empresa_id}&created_at=gte.{desde}&select=estado"
            req = urllib.request.Request(
                f"{url}/rest/v1/followup_tasks?{qs}",
                headers={"apikey": key, "Authorization": f"Bearer {key}", "Accept-Profile": _SCHEMA},
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                return json.loads(r.read().decode())
        except Exception:
            return []
