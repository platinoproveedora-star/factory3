"""CRUD de RFCs administrados por usuario. Valida formato RFC SAT antes de cualquier operación."""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

# Regex SAT oficial: personas morales 3 letras + 6 fecha + 3 homoclave
#                   personas físicas 4 letras + 6 fecha + 3 homoclave
_RFC_RE = re.compile(
    r"^[A-ZÑ&]{3,4}\d{6}[A-Z\d]{3}$",
    re.IGNORECASE,
)


class SecurityManagedRfcService:

    def ejecutar(self, context: dict) -> dict:
        action  = (context.get("action") or "list").strip()
        user_id = (context.get("user_id") or "").strip()

        url = (context.get("platform_supabase_url") or
               os.getenv("PLATFORM_SUPABASE_URL", "")).rstrip("/")
        key = (context.get("platform_supabase_service_role_key") or
               os.getenv("PLATFORM_SUPABASE_SERVICE_ROLE_KEY", ""))

        if not user_id:
            return {"ok": False, "error": "user_id requerido"}
        if not url or not key:
            return {"ok": False, "error": "Faltan PLATFORM_SUPABASE_URL o PLATFORM_SUPABASE_SERVICE_ROLE_KEY"}

        if action == "create":
            return self._create(context, url, key, user_id)
        if action == "list":
            return self._list(context, url, key, user_id)
        if action == "delete":
            return self._delete(context, url, key, user_id)
        if action == "assign_company":
            return self._assign_company(context, url, key, user_id)
        return {"ok": False, "error": f"action inválido: {action}. Usa create|list|delete|assign_company"}

    def _create(self, context: dict, url: str, key: str, user_id: str) -> dict:
        rfc        = (context.get("rfc") or "").strip().upper()
        label      = (context.get("label") or "").strip()
        company_id = (context.get("company_id") or "").strip() or None

        if not rfc or not _RFC_RE.match(rfc):
            return {"ok": False, "error": f"RFC inválido: '{rfc}'. Formato SAT requerido."}

        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run", "data": {"rfc": rfc, "user_id": user_id, "company_id": company_id}}

        try:
            rows = self._pg_post(url, key, "/rest/v1/managed_rfcs", {
                "owner_user_id": user_id,
                "rfc":           rfc,
                "label":         label,
                "company_id":    company_id,
            }, schema="conta4all")
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            if e.code == 409 or "duplicate" in body.lower():
                return {"ok": False, "error": f"RFC '{rfc}' ya está registrado para este usuario"}
            return {"ok": False, "error": f"Supabase {e.code}: {body[:200]}"}

        row = rows[0] if rows else {}
        return {
            "ok":      True,
            "message": f"RFC '{rfc}' registrado",
            "data":    {"managed_rfc_id": row.get("id"), "rfc": rfc, "label": label, "company_id": company_id},
        }

    def _list(self, context: dict, url: str, key: str, user_id: str) -> dict:
        company_id = (context.get("company_id") or "").strip()
        qs = f"?owner_user_id=eq.{urllib.parse.quote(user_id)}&select=id,rfc,label,company_id,created_at&order=created_at.asc"
        if company_id:
            qs += f"&company_id=eq.{urllib.parse.quote(company_id)}"
        rows = self._pg_get(url, key, f"/rest/v1/managed_rfcs{qs}", schema="conta4all")
        return {
            "ok":      True,
            "message": f"{len(rows)} RFC(s) registrados",
            "data":    {"rfcs": rows, "total": len(rows)},
        }

    def _assign_company(self, context: dict, url: str, key: str, user_id: str) -> dict:
        managed_rfc_id = (context.get("managed_rfc_id") or "").strip()
        company_id     = (context.get("company_id") or "").strip() or None
        if not managed_rfc_id:
            return {"ok": False, "error": "managed_rfc_id requerido"}

        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run", "data": {"managed_rfc_id": managed_rfc_id, "company_id": company_id}}

        qs = f"?id=eq.{urllib.parse.quote(managed_rfc_id)}&owner_user_id=eq.{urllib.parse.quote(user_id)}"
        rows = self._pg_patch(url, key, f"/rest/v1/managed_rfcs{qs}", {"company_id": company_id}, schema="conta4all")
        if not rows:
            return {"ok": False, "error": "RFC no encontrado para este usuario"}
        return {"ok": True, "message": "Empresa asignada", "data": {"managed_rfc_id": managed_rfc_id, "company_id": company_id}}

    def _delete(self, context: dict, url: str, key: str, user_id: str) -> dict:
        managed_rfc_id = (context.get("managed_rfc_id") or "").strip()
        if not managed_rfc_id:
            return {"ok": False, "error": "managed_rfc_id requerido para delete"}

        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run — RFC no eliminado"}

        qs = f"?id=eq.{urllib.parse.quote(managed_rfc_id)}&owner_user_id=eq.{urllib.parse.quote(user_id)}"
        self._pg_delete(url, key, f"/rest/v1/managed_rfcs{qs}", schema="conta4all")
        return {"ok": True, "message": f"RFC eliminado: {managed_rfc_id}"}

    def _pg_get(self, url: str, key: str, path: str, schema: str = "platform") -> list:
        req = urllib.request.Request(
            f"{url}{path}",
            headers={
                "apikey":         key,
                "Authorization":  f"Bearer {key}",
                "Accept-Profile": schema,
                "User-Agent":     "FactoryFactory/0.1 (+https://github.com/)",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _pg_post(self, url: str, key: str, path: str, row: dict, schema: str = "platform") -> list:
        req = urllib.request.Request(
            f"{url}{path}",
            data=json.dumps(row).encode("utf-8"),
            headers={
                "apikey":          key,
                "Authorization":   f"Bearer {key}",
                "Content-Type":    "application/json",
                "Content-Profile": schema,
                "Prefer":          "return=representation",
                "User-Agent":      "FactoryFactory/0.1 (+https://github.com/)",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _pg_patch(self, url: str, key: str, path: str, row: dict, schema: str = "platform") -> list:
        req = urllib.request.Request(
            f"{url}{path}",
            data=json.dumps(row).encode("utf-8"),
            headers={
                "apikey":          key,
                "Authorization":   f"Bearer {key}",
                "Content-Type":    "application/json",
                "Content-Profile": schema,
                "Prefer":          "return=representation",
                "User-Agent":      "FactoryFactory/0.1 (+https://github.com/)",
            },
            method="PATCH",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _pg_delete(self, url: str, key: str, path: str, schema: str = "platform") -> None:
        req = urllib.request.Request(
            f"{url}{path}",
            headers={
                "apikey":          key,
                "Authorization":   f"Bearer {key}",
                "Content-Profile": schema,
                "User-Agent":      "FactoryFactory/0.1 (+https://github.com/)",
            },
            method="DELETE",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
