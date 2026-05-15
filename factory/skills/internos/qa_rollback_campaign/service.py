"""Rollback seguro: pausa campaña Meta + backup config + recuperación."""
from __future__ import annotations

import json
import os
import urllib.request
import urllib.parse
from datetime import datetime, timezone

_VERSION = "v24.0"
_UA = "FactoryFactory/0.1 (+https://github.com/)"
_BACKUP_TABLE = "qa_campaign_backups"


class QARollbackCampaignService:

    def ejecutar(self, context: dict) -> dict:
        action = context.get("action", "backup_and_pause")

        if action == "backup_and_pause":
            return self._backup_and_pause(context)
        if action == "restore":
            return self._restore(context)
        if action == "list_backups":
            return self._list_backups(context)
        if action == "ensure_table":
            return self._ensure_table(context)
        return {"ok": False, "error": f"action inválida: {action}. Opciones: backup_and_pause, restore, list_backups, ensure_table"}

    # ── BACKUP + PAUSA ───────────────────────────────────────────────────────

    def _backup_and_pause(self, context: dict) -> dict:
        campaign_id = (context.get("campaign_id") or "").strip()
        company_id  = (context.get("company_id") or "").strip()

        if not campaign_id:
            return {"ok": False, "error": "campaign_id requerido"}
        if not company_id:
            return {"ok": False, "error": "company_id requerido"}

        token = context.get("meta_access_token") or os.getenv("META_ACCESS_TOKEN", "")
        if not token:
            return {"ok": False, "error": "META_ACCESS_TOKEN requerido"}

        # 1. Leer estado actual de la campaña
        try:
            camp_data = self._meta_get(campaign_id, {
                "fields": "id,name,status,objective,daily_budget,lifetime_budget,special_ad_categories"
            }, token)
        except Exception as exc:
            return {"ok": False, "error": f"No se pudo leer campaña Meta: {exc}"}

        if "error" in camp_data:
            return {"ok": False, "error": f"Meta API: {camp_data['error'].get('message', str(camp_data['error']))}"}

        estado_previo = camp_data.get("status", "DESCONOCIDO")
        backup_payload = {
            "campaign_id":  campaign_id,
            "company_id":   company_id,
            "estado_previo": estado_previo,
            "datos_campana": json.dumps(camp_data, ensure_ascii=False),
            "motivo":        context.get("motivo", "rollback_manual"),
            "backed_up_at":  datetime.now(timezone.utc).isoformat(),
        }

        if context.get("dry_run", False):
            return {
                "ok": True,
                "dry_run": True,
                "data": {
                    "accion": "backup_and_pause",
                    "campaign_id": campaign_id,
                    "estado_previo": estado_previo,
                    "backup": backup_payload,
                },
            }

        # 2. Guardar backup en Supabase
        backup_result = self._supabase_insert(_BACKUP_TABLE, backup_payload, context)
        if not backup_result.get("ok"):
            return {**backup_result, "etapa": "backup"}

        # 3. Pausar campaña en Meta
        if estado_previo != "PAUSED":
            try:
                pause_result = self._meta_update(campaign_id, {"status": "PAUSED"}, token)
                if "error" in pause_result:
                    return {"ok": False, "error": f"Campaña no pausada: {pause_result['error']}", "etapa": "pause"}
                pausada = True
            except Exception as exc:
                return {"ok": False, "error": f"Error al pausar: {exc}", "etapa": "pause"}
        else:
            pausada = False  # ya estaba pausada

        return {
            "ok": True,
            "message": (
                f"Campaña {campaign_id} pausada y backup guardado"
                if pausada
                else f"Campaña {campaign_id} ya estaba PAUSED — backup guardado"
            ),
            "data": {
                "campaign_id":  campaign_id,
                "company_id":   company_id,
                "estado_previo": estado_previo,
                "estado_actual": "PAUSED",
                "backup_id":    backup_result.get("data", {}).get("id"),
                "backed_up_at": backup_payload["backed_up_at"],
            },
        }

    # ── RESTAURAR DESDE BACKUP ───────────────────────────────────────────────

    def _restore(self, context: dict) -> dict:
        backup_id   = context.get("backup_id")
        campaign_id = (context.get("campaign_id") or "").strip()

        if not backup_id and not campaign_id:
            return {"ok": False, "error": "backup_id o campaign_id requerido"}

        token = context.get("meta_access_token") or os.getenv("META_ACCESS_TOKEN", "")
        if not token:
            return {"ok": False, "error": "META_ACCESS_TOKEN requerido"}

        # Buscar backup
        try:
            backups = self._supabase_select_backups(backup_id, campaign_id, context)
        except Exception as exc:
            return {"ok": False, "error": f"Error leyendo backups: {exc}"}

        if not backups:
            return {"ok": False, "error": "No se encontró backup para restaurar"}

        backup = backups[0]
        estado_previo = backup.get("estado_previo", "PAUSED")
        camp_id = backup.get("campaign_id")

        if context.get("dry_run", False):
            return {
                "ok": True,
                "dry_run": True,
                "data": {"accion": "restore", "campaign_id": camp_id, "restaurar_a": estado_previo},
            }

        try:
            result = self._meta_update(camp_id, {"status": estado_previo}, token)
            if "error" in result:
                return {"ok": False, "error": f"Meta no restauró estado: {result['error']}"}
        except Exception as exc:
            return {"ok": False, "error": f"Error restaurando: {exc}"}

        return {
            "ok": True,
            "message": f"Campaña {camp_id} restaurada a estado {estado_previo}",
            "data": {"campaign_id": camp_id, "estado_restaurado": estado_previo, "backup": backup},
        }

    # ── LISTAR BACKUPS ───────────────────────────────────────────────────────

    def _list_backups(self, context: dict) -> dict:
        company_id  = context.get("company_id")
        campaign_id = context.get("campaign_id")
        limit       = int(context.get("limit", 20))

        try:
            backups = self._supabase_select_backups(None, campaign_id, context,
                                                    company_id=company_id, limit=limit)
            return {"ok": True, "data": {"total": len(backups), "backups": backups}}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    # ── CREAR TABLA ──────────────────────────────────────────────────────────

    def _ensure_table(self, context: dict) -> dict:
        sql = f"""
CREATE TABLE IF NOT EXISTS public.{_BACKUP_TABLE} (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id    text NOT NULL,
  company_id     text NOT NULL,
  estado_previo  text NOT NULL,
  datos_campana  text NOT NULL DEFAULT '{{}}',
  motivo         text NOT NULL DEFAULT 'rollback_manual',
  backed_up_at   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_backups_campaign ON public.{_BACKUP_TABLE}(campaign_id);
CREATE INDEX IF NOT EXISTS idx_backups_company  ON public.{_BACKUP_TABLE}(company_id);
CREATE INDEX IF NOT EXISTS idx_backups_time     ON public.{_BACKUP_TABLE}(backed_up_at DESC);
""".strip()

        if context.get("dry_run", False):
            return {"ok": True, "dry_run": True, "sql": sql}

        try:
            return self._management_sql(sql, context)
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    # ── META HELPERS ─────────────────────────────────────────────────────────

    def _meta_get(self, obj_id: str, params: dict, token: str) -> dict:
        params["access_token"] = token
        qs  = urllib.parse.urlencode(params)
        url = f"https://graph.facebook.com/{_VERSION}/{obj_id}?{qs}"
        req = urllib.request.Request(url, headers={"User-Agent": _UA})
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode())

    def _meta_update(self, obj_id: str, payload: dict, token: str) -> dict:
        payload["access_token"] = token
        data = urllib.parse.urlencode(payload).encode()
        url  = f"https://graph.facebook.com/{_VERSION}/{obj_id}"
        req  = urllib.request.Request(url, data=data, headers={"User-Agent": _UA}, method="POST")
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode())

    # ── SUPABASE HELPERS ─────────────────────────────────────────────────────

    def _supabase_insert(self, table: str, row: dict, context: dict) -> dict:
        url = (context.get("supabase_url") or os.getenv("SUPABASE_URL", "")).rstrip("/")
        key = context.get("supabase_service_role_key") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        if not url or not key:
            return {"ok": False, "error": "SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY requeridos"}
        data = json.dumps(row).encode("utf-8")
        req  = urllib.request.Request(
            f"{url}/rest/v1/{table}", data=data, method="POST",
            headers={
                "apikey": key, "Authorization": f"Bearer {key}",
                "Content-Type": "application/json", "Prefer": "return=representation",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            body = json.loads(r.read().decode())
            inserted = body[0] if isinstance(body, list) and body else {}
            return {"ok": True, "data": inserted}

    def _supabase_select_backups(self, backup_id, campaign_id, context,
                                 company_id=None, limit=20) -> list:
        url = (context.get("supabase_url") or os.getenv("SUPABASE_URL", "")).rstrip("/")
        key = context.get("supabase_service_role_key") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        filters: list[str] = []
        if backup_id:
            filters.append(f"id=eq.{urllib.parse.quote(str(backup_id))}")
        if campaign_id:
            filters.append(f"campaign_id=eq.{urllib.parse.quote(campaign_id)}")
        if company_id:
            filters.append(f"company_id=eq.{urllib.parse.quote(company_id)}")
        qs = "&".join(filters)
        endpoint = f"{url}/rest/v1/{_BACKUP_TABLE}?order=backed_up_at.desc&limit={limit}"
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
            return {"ok": False, "error": "SUPABASE_PROJECT_REF y SUPABASE_ACCESS_TOKEN requeridos"}
        url  = f"https://api.supabase.com/v1/projects/{ref}/database/query"
        data = json.dumps({"query": sql}).encode("utf-8")
        req  = urllib.request.Request(
            url, data=data, method="POST",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            return {"ok": True, "data": json.loads(r.read().decode())}
