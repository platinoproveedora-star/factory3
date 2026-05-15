"""Log estructurado por empresa/campaña/skill con trazabilidad de cada ejecución."""
from __future__ import annotations

import json
import os
import traceback
import urllib.request
import urllib.parse
from datetime import datetime, timezone


_SEMAFORO = {"ok": "OK", "error": "ERROR", "warning": "WARN"}
_TABLE = "qa_execution_logs"


class QACampaignLoggerService:

    def ejecutar(self, context: dict) -> dict:
        action = context.get("action", "log")

        if action == "log":
            return self._log(context)
        if action == "query":
            return self._query(context)
        if action == "ensure_table":
            return self._ensure_table(context)
        return {"ok": False, "error": f"action desconocida: {action}. Opciones: log, query, ensure_table"}

    # ── REGISTRAR UNA EJECUCIÓN ──────────────────────────────────────────────

    def _log(self, context: dict) -> dict:
        company_id   = (context.get("company_id") or "").strip()
        campaign_id  = (context.get("campaign_id") or "").strip()
        skill_name   = (context.get("skill_name") or "").strip()
        status       = context.get("status", "ok")
        message      = context.get("message", "")
        payload      = context.get("payload") or {}
        error_detail = context.get("error_detail") or ""

        if not company_id:
            return {"ok": False, "error": "company_id requerido"}
        if not skill_name:
            return {"ok": False, "error": "skill_name requerido"}

        now_utc = datetime.now(timezone.utc).isoformat()
        row = {
            "company_id":   company_id,
            "campaign_id":  campaign_id,
            "skill_name":   skill_name,
            "status":       status,
            "semaforo":     _SEMAFORO.get(status, status.upper()),
            "message":      message,
            "payload":      json.dumps(payload, ensure_ascii=False),
            "error_detail": error_detail,
            "executed_at":  now_utc,
        }

        if context.get("dry_run", False):
            return {"ok": True, "dry_run": True, "data": row}

        try:
            result = self._supabase_insert(row, context)
            if not result.get("ok"):
                return result
            return {
                "ok": True,
                "message": f"[{_SEMAFORO.get(status, status.upper())}] {company_id}/{campaign_id}/{skill_name} — {message}",
                "data": {"log_id": result.get("data", {}).get("id"), "executed_at": now_utc},
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc), "traceback": traceback.format_exc()}

    # ── CONSULTAR LOGS ───────────────────────────────────────────────────────

    def _query(self, context: dict) -> dict:
        company_id  = context.get("company_id")
        campaign_id = context.get("campaign_id")
        skill_name  = context.get("skill_name")
        status      = context.get("status")
        limit       = int(context.get("limit", 50))

        filters: list[str] = []
        if company_id:
            filters.append(f"company_id=eq.{urllib.parse.quote(company_id)}")
        if campaign_id:
            filters.append(f"campaign_id=eq.{urllib.parse.quote(campaign_id)}")
        if skill_name:
            filters.append(f"skill_name=eq.{urllib.parse.quote(skill_name)}")
        if status:
            filters.append(f"status=eq.{urllib.parse.quote(status)}")

        try:
            rows = self._supabase_select(filters, limit, context)
            return {
                "ok": True,
                "data": {
                    "total": len(rows),
                    "logs": rows,
                    "filtros": {
                        "company_id": company_id,
                        "campaign_id": campaign_id,
                        "skill_name": skill_name,
                        "status": status,
                    },
                },
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    # ── CREAR TABLA SI NO EXISTE ─────────────────────────────────────────────

    def _ensure_table(self, context: dict) -> dict:
        sql = f"""
CREATE TABLE IF NOT EXISTS public.{_TABLE} (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id   text NOT NULL,
  campaign_id  text NOT NULL DEFAULT '',
  skill_name   text NOT NULL,
  status       text NOT NULL DEFAULT 'ok',
  semaforo     text NOT NULL DEFAULT 'OK',
  message      text NOT NULL DEFAULT '',
  payload      text NOT NULL DEFAULT '{{}}',
  error_detail text NOT NULL DEFAULT '',
  executed_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_qa_logs_company  ON public.{_TABLE}(company_id);
CREATE INDEX IF NOT EXISTS idx_qa_logs_campaign ON public.{_TABLE}(campaign_id);
CREATE INDEX IF NOT EXISTS idx_qa_logs_skill    ON public.{_TABLE}(skill_name);
CREATE INDEX IF NOT EXISTS idx_qa_logs_status   ON public.{_TABLE}(status);
CREATE INDEX IF NOT EXISTS idx_qa_logs_time     ON public.{_TABLE}(executed_at DESC);
""".strip()

        if context.get("dry_run", False):
            return {"ok": True, "dry_run": True, "sql": sql}

        try:
            result = self._management_sql(sql, context)
            return result
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    # ── SUPABASE HELPERS ─────────────────────────────────────────────────────

    def _supabase_insert(self, row: dict, context: dict) -> dict:
        url  = (context.get("supabase_url") or os.getenv("SUPABASE_URL", "")).rstrip("/")
        key  = context.get("supabase_service_role_key") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        if not url or not key:
            return {"ok": False, "error": "SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY requeridos"}

        endpoint = f"{url}/rest/v1/{_TABLE}"
        data = json.dumps(row).encode("utf-8")
        req = urllib.request.Request(
            endpoint, data=data, method="POST",
            headers={
                "apikey": key, "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "Prefer": "return=representation",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            body = json.loads(r.read().decode())
            inserted = body[0] if isinstance(body, list) and body else {}
            return {"ok": True, "data": inserted}

    def _supabase_select(self, filters: list[str], limit: int, context: dict) -> list:
        url = (context.get("supabase_url") or os.getenv("SUPABASE_URL", "")).rstrip("/")
        key = context.get("supabase_service_role_key") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        qs  = "&".join(filters) if filters else ""
        endpoint = f"{url}/rest/v1/{_TABLE}?order=executed_at.desc&limit={limit}"
        if qs:
            endpoint += f"&{qs}"
        req = urllib.request.Request(
            endpoint,
            headers={"apikey": key, "Authorization": f"Bearer {key}", "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())

    def _management_sql(self, sql: str, context: dict) -> dict:
        ref   = context.get("supabase_project_ref") or os.getenv("SUPABASE_PROJECT_REF", "")
        token = context.get("supabase_access_token") or os.getenv("SUPABASE_ACCESS_TOKEN", "")
        if not ref or not token:
            return {"ok": False, "error": "SUPABASE_PROJECT_REF y SUPABASE_ACCESS_TOKEN requeridos para ensure_table"}
        url  = f"https://api.supabase.com/v1/projects/{ref}/database/query"
        data = json.dumps({"query": sql}).encode("utf-8")
        req  = urllib.request.Request(
            url, data=data, method="POST",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            body = json.loads(r.read().decode())
            return {"ok": True, "data": body}
