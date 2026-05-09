"""Supabase connection for dashboard."""
from __future__ import annotations
import json, os, urllib.request
from pathlib import Path

def _load_env() -> None:
    env = Path(__file__).parent.parent.parent / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8", errors="replace").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        k, v = raw.split("=", 1)
        k = k.strip(); v = v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v

_load_env()


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
