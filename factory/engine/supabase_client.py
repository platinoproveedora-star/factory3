"""Shared Supabase helpers for Factory skills."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SupabaseConfig:
    url: str
    rest_key: str
    access_token: str
    project_ref: str


class SupabaseClient:
    """Small urllib based client for Supabase REST and Management APIs."""

    def __init__(self, context: dict[str, Any] | None = None):
        self.context = context or {}
        self.config = self._load_config(self.context)

    def check_config(self, require_rest: bool = False, require_management: bool = False) -> dict[str, Any]:
        missing = []
        if require_rest:
            if not self.config.url:
                missing.append("SUPABASE_URL")
            if not self.config.rest_key:
                missing.append("SUPABASE_SERVICE_ROLE_KEY o SUPABASE_ANON_KEY")
        if require_management:
            if not self.config.access_token:
                missing.append("SUPABASE_ACCESS_TOKEN")
            if not self.config.project_ref:
                missing.append("SUPABASE_PROJECT_REF")
        if missing:
            return {"ok": False, "error": "faltan credenciales", "data": {"missing": missing}}
        return {"ok": True, "data": self.public_config()}

    def public_config(self) -> dict[str, Any]:
        return {
            "url": self.config.url,
            "project_ref": self.config.project_ref,
            "has_rest_key": bool(self.config.rest_key),
            "has_access_token": bool(self.config.access_token),
        }

    def management_query(self, query: str, read_only: bool = False) -> dict[str, Any]:
        check = self.check_config(require_management=True)
        if not check.get("ok"):
            return check
        endpoint = f"https://api.supabase.com/v1/projects/{self.config.project_ref}/database/query"
        payload = {"query": query}
        if read_only:
            payload["read_only"] = True
        return self._request("POST", endpoint, payload, {"Authorization": f"Bearer {self.config.access_token}"})

    def rest_select(
        self,
        table: str,
        filters: dict[str, Any] | None = None,
        select: str = "*",
        limit: int | None = None,
        order: str | None = None,
    ) -> dict[str, Any]:
        check = self.check_config(require_rest=True)
        if not check.get("ok"):
            return check
        params: dict[str, str] = {"select": select}
        for key, value in (filters or {}).items():
            params[key] = self._filter_value(value)
        if limit is not None:
            params["limit"] = str(limit)
        if order:
            params["order"] = order
        endpoint = self._rest_url(table, params)
        return self._request("GET", endpoint, None, self._rest_headers())

    def rest_insert(self, table: str, rows: list[dict[str, Any]] | dict[str, Any]) -> dict[str, Any]:
        check = self.check_config(require_rest=True)
        if not check.get("ok"):
            return check
        endpoint = self._rest_url(table)
        return self._request("POST", endpoint, rows, self._rest_headers(return_representation=True))

    def rest_update(self, table: str, values: dict[str, Any], filters: dict[str, Any]) -> dict[str, Any]:
        check = self.check_config(require_rest=True)
        if not check.get("ok"):
            return check
        endpoint = self._rest_url(table, self._filter_params(filters))
        return self._request("PATCH", endpoint, values, self._rest_headers(return_representation=True))

    def rest_delete(self, table: str, filters: dict[str, Any]) -> dict[str, Any]:
        check = self.check_config(require_rest=True)
        if not check.get("ok"):
            return check
        endpoint = self._rest_url(table, self._filter_params(filters))
        return self._request("DELETE", endpoint, None, self._rest_headers(return_representation=True))

    def rest_upsert(self, table: str, rows: list[dict[str, Any]] | dict[str, Any], on_conflict: str = "") -> dict[str, Any]:
        check = self.check_config(require_rest=True)
        if not check.get("ok"):
            return check
        params = {"on_conflict": on_conflict} if on_conflict else {}
        endpoint = self._rest_url(table, params)
        headers = self._rest_headers(return_representation=True)
        headers["Prefer"] = "resolution=merge-duplicates,return=representation"
        return self._request("POST", endpoint, rows, headers)

    def rpc(self, function_name: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        check = self.check_config(require_rest=True)
        if not check.get("ok"):
            return check
        endpoint = self._rest_url(f"rpc/{function_name}")
        return self._request("POST", endpoint, params or {}, self._rest_headers())

    def _rest_headers(self, return_representation: bool = False) -> dict[str, str]:
        headers = {
            "apikey": self.config.rest_key,
            "Authorization": f"Bearer {self.config.rest_key}",
        }
        if return_representation:
            headers["Prefer"] = "return=representation"
        return headers

    def _rest_url(self, path: str, params: dict[str, str] | None = None) -> str:
        base = f"{self.config.url.rstrip('/')}/rest/v1/{path.strip('/')}"
        if not params:
            return base
        return f"{base}?{urllib.parse.urlencode(params)}"

    def _filter_params(self, filters: dict[str, Any]) -> dict[str, str]:
        return {key: self._filter_value(value) for key, value in filters.items()}

    def _filter_value(self, value: Any) -> str:
        text = str(value)
        operators = ("eq.", "neq.", "gt.", "gte.", "lt.", "lte.", "like.", "ilike.", "in.", "is.", "cs.", "cd.", "ov.")
        if text.startswith(operators):
            return text
        return f"eq.{text}"

    def _request(
        self,
        method: str,
        endpoint: str,
        payload: Any,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request_headers = {
            "Content-Type": "application/json",
            "User-Agent": "FactoryFactory/0.1 (+https://github.com/)",
        }
        request_headers.update(headers or {})
        req = urllib.request.Request(endpoint, data=body, method=method, headers=request_headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                raw = response.read().decode("utf-8")
                data = json.loads(raw) if raw else None
            return {"ok": True, "data": data}
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            return {"ok": False, "error": f"HTTP {exc.code}: {raw}", "data": {"endpoint": endpoint}}
        except Exception as exc:
            return {"ok": False, "error": str(exc), "data": {"endpoint": endpoint}}

    def _load_config(self, context: dict[str, Any]) -> SupabaseConfig:
        url = os.getenv("SUPABASE_URL", context.get("supabase_url", "")).strip()
        rest_key = (
            os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            or os.getenv("SUPABASE_SERVICE_KEY")
            or os.getenv("SUPABASE_ANON_KEY")
            or context.get("supabase_service_role_key")
            or context.get("supabase_service_key")
            or context.get("supabase_anon_key")
            or ""
        )
        access_token = os.getenv("SUPABASE_ACCESS_TOKEN", context.get("supabase_access_token", "")).strip()
        project_ref = os.getenv("SUPABASE_PROJECT_REF", context.get("supabase_project_ref", "")).strip()
        if not project_ref and url:
            project_ref = self._project_ref_from_url(url)
        return SupabaseConfig(url=url, rest_key=str(rest_key).strip(), access_token=access_token, project_ref=project_ref)

    def _project_ref_from_url(self, url: str) -> str:
        host = urllib.parse.urlparse(url).hostname or ""
        if host.endswith(".supabase.co"):
            return host.split(".", 1)[0]
        return ""
