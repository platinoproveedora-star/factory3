"""Supabase helpers for Freelance Center, schema freelance."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request


SCHEMA = "freelance"
LAST_ERROR = ""


def configured() -> bool:
    return bool(os.getenv("SUPABASE_URL", "").strip() and _key())


def _key() -> str:
    return (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        or os.getenv("SUPABASE_KEY", "").strip()
        or os.getenv("SUPABASE_ANON_KEY", "").strip()
    )


def _headers(write: bool = False) -> dict:
    key = _key()
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    headers["Content-Profile" if write else "Accept-Profile"] = SCHEMA
    if write:
        headers["Prefer"] = "return=representation"
    return headers


def _url(table: str, params: dict | str | None = None) -> str:
    base = os.getenv("SUPABASE_URL", "").rstrip("/")
    if isinstance(params, dict):
        query = urllib.parse.urlencode(params, doseq=True)
    else:
        query = params or ""
    return f"{base}/rest/v1/{table}?{query}" if query else f"{base}/rest/v1/{table}"


def select(table: str, params: dict | str | None = None) -> list[dict]:
    global LAST_ERROR
    if not configured():
        LAST_ERROR = "SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY no configurados"
        return []
    req = urllib.request.Request(_url(table, params or "select=*&limit=1000"), headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            LAST_ERROR = ""
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        LAST_ERROR = f"{table} SELECT HTTP {exc.code}: {exc.read().decode()}"
        return []
    except Exception as exc:
        LAST_ERROR = f"{table} SELECT: {exc}"
        return []


def insert(table: str, data: dict) -> dict | None:
    global LAST_ERROR
    if not configured():
        LAST_ERROR = "SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY no configurados"
        return None
    body = json.dumps(data, ensure_ascii=False).encode()
    req = urllib.request.Request(_url(table), data=body, headers=_headers(write=True), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            LAST_ERROR = ""
            rows = json.loads(response.read().decode())
            return rows[0] if rows else {}
    except urllib.error.HTTPError as exc:
        LAST_ERROR = f"{table} INSERT HTTP {exc.code}: {exc.read().decode()}"
        return None
    except Exception as exc:
        LAST_ERROR = f"{table} INSERT: {exc}"
        return None


def last_error() -> str:
    return LAST_ERROR
