"""Service for meta_connection_check - validates a Meta/Instagram connection."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request


PUBLISHING_SCOPES = {"instagram_basic", "instagram_content_publish", "pages_show_list"}
INSIGHTS_SCOPES = {"instagram_basic", "instagram_manage_insights"}
COMMENTS_SCOPES = {"instagram_basic", "instagram_manage_comments"}
MESSAGES_SCOPES = {"instagram_manage_messages"}


class MetaConnectionCheckService:

    def ejecutar(self, context: dict) -> dict:
        access_token = self._get_text(context, "access_token") or os.getenv("META_ACCESS_TOKEN") or os.getenv("IG_ACCESS_TOKEN")
        page_id = self._get_text(context, "page_id") or os.getenv("META_PAGE_ID") or os.getenv("IG_PAGE_ID")
        ig_user_id = (
            self._get_text(context, "ig_user_id")
            or self._get_text(context, "instagram_business_account")
            or os.getenv("META_IG_USER_ID")
            or os.getenv("IG_BUSINESS_ACCOUNT_ID")
        )
        graph_version = self._graph_version(context)
        supplied_scopes = self._normalize_scopes(context.get("scopes") or context.get("permissions") or context.get("permisos"))

        if context.get("dry_run", False):
            return self._dry_run(access_token, page_id, ig_user_id, supplied_scopes, graph_version)
        if not access_token:
            return {"ok": False, "error": "access_token es requerido en context, META_ACCESS_TOKEN o IG_ACCESS_TOKEN"}
        if not page_id:
            return {"ok": False, "error": "page_id es requerido en context, META_PAGE_ID o IG_PAGE_ID"}

        checks: dict = {}
        errors: list[dict] = []
        me = self._safe_call("GET", "/me", access_token, graph_version, {"fields": "id,name"})
        checks["access_token"] = self._check_result(me)
        if not me["ok"]:
            errors.append({"target": "access_token", "error": me["error"]})

        page = self._safe_call(
            "GET",
            f"/{page_id}",
            access_token,
            graph_version,
            {"fields": "id,name,instagram_business_account{id,username,account_type}"},
        )
        checks["page"] = self._check_result(page)
        if page["ok"]:
            ig_account = page["data"].get("instagram_business_account") or {}
            ig_user_id = ig_user_id or ig_account.get("id")
        else:
            errors.append({"target": "page_id", "error": page["error"]})

        ig = {"ok": False, "data": {}, "error": "ig_user_id no provisto ni encontrado en page.instagram_business_account"}
        if ig_user_id:
            ig = self._safe_call(
                "GET",
                f"/{ig_user_id}",
                access_token,
                graph_version,
                {"fields": "id,username,account_type"},
            )
        checks["instagram_business_account"] = self._check_result(ig)
        if not ig["ok"]:
            errors.append({"target": "ig_user_id", "error": ig["error"]})

        scopes = supplied_scopes
        permissions_source = "input"
        if not scopes:
            perms = self._safe_call("GET", "/me/permissions", access_token, graph_version)
            if perms["ok"]:
                scopes = self._scopes_from_permissions(perms["data"].get("data", []))
                permissions_source = "graph"
            else:
                permissions_source = "unavailable"
                errors.append({"target": "permissions", "error": perms["error"]})

        ready_flags = self._ready_flags(bool(access_token), bool(page["ok"]), bool(ig["ok"]), scopes)
        ok = checks["access_token"]["ok"] and checks["page"]["ok"] and checks["instagram_business_account"]["ok"]
        return {
            "ok": ok,
            "data": {
                "graph_version": graph_version,
                "page_id": page_id,
                "ig_user_id": ig_user_id,
                "checks": checks,
                "scopes": sorted(scopes),
                "permissions_source": permissions_source,
                "ready_flags": ready_flags,
                "errors": errors,
            },
        }

    def _dry_run(self, access_token: str | None, page_id: str | None, ig_user_id: str | None, scopes: set[str], graph_version: str) -> dict:
        ready_flags = self._ready_flags(bool(access_token), bool(page_id), bool(ig_user_id), scopes)
        return {
            "ok": True,
            "message": "dry_run",
            "data": {
                "graph_version": graph_version,
                "page_id": page_id,
                "ig_user_id": ig_user_id,
                "scopes": sorted(scopes),
                "ready_flags": ready_flags,
            },
        }

    def _ready_flags(self, has_token: bool, has_page: bool, has_ig: bool, scopes: set[str]) -> dict:
        base = has_token and has_page and has_ig
        return {
            "publishing": self._flag(base, scopes, PUBLISHING_SCOPES),
            "insights": self._flag(base, scopes, INSIGHTS_SCOPES),
            "comments": self._flag(base, scopes, COMMENTS_SCOPES),
            "messages": self._flag(has_token and has_page, scopes, MESSAGES_SCOPES),
        }

    def _flag(self, base_ready: bool, scopes: set[str], required: set[str]) -> dict:
        missing = sorted(required - scopes) if scopes else sorted(required)
        return {"ready": bool(base_ready and scopes and not missing), "missing_scopes": missing}

    def _safe_call(self, method: str, path: str, access_token: str, graph_version: str, params: dict | None = None) -> dict:
        try:
            return {"ok": True, "data": self._call_meta(method, path, access_token, graph_version, params)}
        except urllib.error.HTTPError as exc:
            return {"ok": False, "data": {}, "error": self._http_error_message(exc)}
        except Exception as exc:
            return {"ok": False, "data": {}, "error": str(exc)}

    def _call_meta(self, method: str, path: str, access_token: str, graph_version: str, params: dict | None = None) -> dict:
        query = {"access_token": access_token}
        if params:
            query.update(params)
        url = f"https://graph.facebook.com/{graph_version}{path}?" + urllib.parse.urlencode(query)
        req = urllib.request.Request(url, method=method.upper())
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

    def _http_error_message(self, exc: urllib.error.HTTPError) -> str:
        try:
            body = json.loads(exc.read().decode("utf-8"))
            return body.get("error", {}).get("message", str(exc))
        except Exception:
            return str(exc)

    def _check_result(self, result: dict) -> dict:
        if result["ok"]:
            return {"ok": True, "data": result["data"]}
        return {"ok": False, "error": result["error"]}

    def _scopes_from_permissions(self, permissions: list) -> set[str]:
        scopes: set[str] = set()
        for item in permissions:
            if isinstance(item, dict) and item.get("status") == "granted" and isinstance(item.get("permission"), str):
                scopes.add(item["permission"])
        return scopes

    def _normalize_scopes(self, value: object) -> set[str]:
        if isinstance(value, str):
            return {part.strip() for part in value.replace(" ", ",").split(",") if part.strip()}
        if isinstance(value, (list, tuple, set)):
            return {str(item).strip() for item in value if str(item).strip()}
        return set()

    def _get_text(self, context: dict, key: str) -> str | None:
        value = context.get(key)
        return value.strip() if isinstance(value, str) and value.strip() else None

    def _graph_version(self, context: dict) -> str:
        return self._get_text(context, "graph_version") or os.getenv("META_GRAPH_API_VERSION") or os.getenv("IG_GRAPH_API_VERSION") or "v24.0"
