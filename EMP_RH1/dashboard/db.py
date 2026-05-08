"""Supabase connection for dashboard."""
from __future__ import annotations
import json, os, urllib.request


def _key() -> str:
    return (os.environ.get("SUPABASE_KEY")
            or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
            or os.environ.get("SUPABASE_ANON_KEY", ""))


def _headers() -> dict:
    key = _key()
    return {
        "apikey":        key,
        "Authorization": f"Bearer {key}",
        "Content-Type":  "application/json",
    }


def _url(table: str, params: str = "") -> str:
    base = os.environ["SUPABASE_URL"].rstrip("/")
    return f"{base}/rest/v1/{table}?{params}" if params else f"{base}/rest/v1/{table}"


def select(table: str, params: str = "select=*&limit=500") -> list:
    req = urllib.request.Request(_url(table, params), headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())
    except Exception:
        return []


def count(table: str, filters: str = "") -> int:
    headers = {**_headers(), "Prefer": "count=exact", "Range": "0-0"}
    params  = f"select=id&{filters}" if filters else "select=id"
    req = urllib.request.Request(_url(table, params), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            cr = r.headers.get("Content-Range", "0/0")
            return int(cr.split("/")[-1]) if "/" in cr else 0
    except Exception:
        return 0
