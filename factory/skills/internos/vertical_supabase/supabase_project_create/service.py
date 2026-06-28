"""Crea un proyecto Supabase nuevo via Management API y devuelve credenciales."""
from __future__ import annotations

import json
import os
import secrets
import time
import urllib.error
import urllib.request

_API = "https://api.supabase.com/v1"
_DEFAULT_REGION = "us-east-1"
_DEFAULT_PLAN   = "free"
_POLL_INTERVAL  = 10   # segundos entre checks de salud
_HEALTHY_STATUS = "ACTIVE_HEALTHY"


class SupabaseProjectCreateService:

    def ejecutar(self, context: dict) -> dict:
        access_token = (context.get("access_token") or
                        os.getenv("SUPABASE_ACCESS_TOKEN", "")).strip()
        if not access_token:
            return {"ok": False, "error": "access_token requerido (o env SUPABASE_ACCESS_TOKEN)"}

        action = (context.get("action") or "create").strip()

        if action == "list_orgs":
            return self._list_orgs(access_token)

        # action == "create"
        name    = (context.get("name") or "").strip()
        org_id  = (context.get("organization_id") or "").strip()
        region  = (context.get("region") or _DEFAULT_REGION).strip()
        plan    = (context.get("plan") or _DEFAULT_PLAN).strip()
        db_pass = (context.get("db_pass") or "").strip()
        wait    = context.get("wait", True)
        wait_s  = int(context.get("wait_seconds", 300))

        if not name:
            return {"ok": False, "error": "name requerido"}
        if not org_id:
            return {"ok": False,
                    "error": "organization_id requerido. Usa action=list_orgs para obtenerlo."}

        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run — proyecto no creado", "data": {
                "name": name, "organization_id": org_id, "region": region, "plan": plan,
            }}

        if not db_pass:
            db_pass = secrets.token_urlsafe(24)

        # 1 — Crear proyecto
        try:
            project = self._api_post(access_token, "/projects", {
                "name":            name,
                "organization_id": org_id,
                "region":          region,
                "plan":            plan,
                "db_pass":         db_pass,
            })
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            return {"ok": False, "error": f"Supabase API {e.code}: {body[:400]}"}
        except Exception as e:
            return {"ok": False, "error": f"Error creando proyecto: {e}"}

        ref = project.get("id") or project.get("ref") or ""
        if not ref:
            return {"ok": False, "error": "Respuesta inesperada — sin project ref",
                    "data": {"raw": project}}

        result = {
            "project_ref": ref,
            "name":        project.get("name", name),
            "region":      project.get("region", region),
            "db_pass":     db_pass,  # solo disponible aquí — NO se puede recuperar después
        }

        # 2 — Esperar salud
        if wait:
            status, elapsed = self._wait_healthy(access_token, ref, wait_s)
            result["status"]         = status
            result["wait_elapsed_s"] = elapsed
            if status != _HEALTHY_STATUS:
                result["warning"] = f"Proyecto creado pero estado={status}. Usa supabase_project_status_check para continuar."
        else:
            result["status"]  = "PENDING"
            result["warning"] = "wait=False — usa supabase_project_status_check para verificar salud antes de continuar."

        # 3 — Obtener API keys (solo si activo)
        if result.get("status") == _HEALTHY_STATUS:
            try:
                keys = self._api_get(access_token, f"/projects/{ref}/api-keys")
                for k in keys:
                    if k.get("name") == "service_role":
                        result["service_role_key"] = k["api_key"]
                    elif k.get("name") == "anon":
                        result["anon_key"] = k["api_key"]
                result["url"] = f"https://{ref}.supabase.co"
            except Exception as e:
                result["warning_keys"] = f"Proyecto activo pero error obteniendo API keys: {e}"

        msg = f"Proyecto '{name}' ({ref}) creado"
        if "url" in result:
            msg += f" — {result['url']}"
        if "db_pass" in result:
            msg += " — GUARDA db_pass AHORA, no se puede recuperar después"

        return {"ok": True, "message": msg, "data": result}

    # ── helpers ──────────────────────────────────────────────────────────────

    def _list_orgs(self, access_token: str) -> dict:
        try:
            orgs = self._api_get(access_token, "/organizations")
        except Exception as e:
            return {"ok": False, "error": f"Error listando orgs: {e}"}
        return {
            "ok":      True,
            "message": f"{len(orgs)} organización(es) disponibles",
            "data":    {"organizations": orgs},
        }

    def _wait_healthy(self, access_token: str, ref: str, max_seconds: int) -> tuple[str, int]:
        start   = time.time()
        status  = "UNKNOWN"
        elapsed = 0
        while elapsed < max_seconds:
            time.sleep(_POLL_INTERVAL)
            elapsed = int(time.time() - start)
            try:
                health = self._api_get(access_token, f"/projects/{ref}/health")
                # La API devuelve lista de servicios; buscamos el estado general
                if isinstance(health, list):
                    statuses = {h.get("status") for h in health}
                    if statuses == {"ACTIVE_HEALTHY"} or all(
                        s in ("ACTIVE_HEALTHY", "COMING_UP") for s in statuses
                    ):
                        status = _HEALTHY_STATUS
                    else:
                        status = next(iter(statuses), "UNKNOWN")
                elif isinstance(health, dict):
                    status = health.get("status", "UNKNOWN")
                else:
                    status = "UNKNOWN"
            except Exception:
                status = "CHECK_FAILED"

            if status == _HEALTHY_STATUS:
                break

        return status, elapsed

    def _api_get(self, token: str, path: str) -> dict | list:
        req = urllib.request.Request(
            f"{_API}{path}",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type":  "application/json",
                "User-Agent":    "FactoryFactory/0.1 (+https://github.com/)",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _api_post(self, token: str, path: str, payload: dict) -> dict:
        req = urllib.request.Request(
            f"{_API}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type":  "application/json",
                "User-Agent":    "FactoryFactory/0.1 (+https://github.com/)",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
