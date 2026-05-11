"""Supabase connection for LOGPLAT dashboard — schema logplat."""
from __future__ import annotations
import json, os, urllib.request


def _key() -> str:
    return (os.environ.get("SUPABASE_KEY")
            or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
            or os.environ.get("SUPABASE_ANON_KEY", ""))


def _headers(write: bool = False) -> dict:
    key = _key()
    h = {
        "apikey":        key,
        "Authorization": f"Bearer {key}",
        "Content-Type":  "application/json",
    }
    h["Content-Profile" if write else "Accept-Profile"] = "logplat"
    if write:
        h["Prefer"] = "return=representation"
    return h


def _url(table: str, params: str = "") -> str:
    base = os.environ.get("SUPABASE_URL", "").rstrip("/")
    return f"{base}/rest/v1/{table}?{params}" if params else f"{base}/rest/v1/{table}"


def select(table: str, params: str = "select=*&limit=1000") -> list:
    req = urllib.request.Request(_url(table, params), headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())
    except Exception:
        return []


def insert(table: str, data: dict) -> bool:
    body = json.dumps(data).encode()
    req  = urllib.request.Request(_url(table), data=body, headers=_headers(write=True), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            r.read()
        return True
    except Exception:
        return False


def delete(table: str, folio: str) -> bool:
    url = _url(table, f"folio=eq.{folio}")
    req = urllib.request.Request(url, headers=_headers(write=True), method="DELETE")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            r.read()
        return True
    except Exception:
        return False


def update(table: str, folio: str, data: dict) -> bool:
    url  = _url(table, f"folio=eq.{folio}")
    body = json.dumps(data).encode()
    req  = urllib.request.Request(url, data=body, headers=_headers(write=True), method="PATCH")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            r.read()
        return True
    except Exception:
        return False
