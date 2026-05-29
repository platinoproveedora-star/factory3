"""
Cliente HTTP compartido para la Vercel API.
Importado por todos los skills de vertical_vercel.
"""
from __future__ import annotations
import json
import os
import urllib.error
import urllib.request

_BASE = "https://api.vercel.com"


def _token() -> str:
    return os.getenv("VERCEL_TOKEN", "")


def _team_id() -> str:
    return os.getenv("VERCEL_TEAM_ID", "")


def _qs(extra: dict | None = None) -> str:
    """Query string con teamId opcional + parámetros extra."""
    params: dict = {}
    tid = _team_id()
    if tid:
        params["teamId"] = tid
    if extra:
        params.update(extra)
    if not params:
        return ""
    return "?" + "&".join(f"{k}={v}" for k, v in params.items())


def _headers(content_type: bool = False) -> dict:
    h = {
        "Authorization": f"Bearer {_token()}",
        "User-Agent": "FactoryFactory/0.1 (+https://github.com/)",
    }
    if content_type:
        h["Content-Type"] = "application/json"
    return h


def _request(method: str, path: str, body: dict | None = None, qs: dict | None = None) -> dict:
    """Ejecuta request a Vercel API. Retorna dict con ok/data/error."""
    if not _token():
        return {"ok": False, "error": "VERCEL_TOKEN no configurado"}

    url = f"{_BASE}{path}{_qs(qs)}"
    data = json.dumps(body).encode() if body is not None else None

    req = urllib.request.Request(
        url,
        data=data,
        headers=_headers(content_type=body is not None),
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode()
            return {"ok": True, "data": json.loads(raw) if raw else {}}
    except urllib.error.HTTPError as e:
        body_err = e.read().decode()
        try:
            detail = json.loads(body_err).get("error", {})
            msg = detail.get("message", body_err[:200])
        except Exception:
            msg = body_err[:200]
        return {"ok": False, "error": f"HTTP {e.code}: {msg}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get(path: str, qs: dict | None = None) -> dict:
    return _request("GET", path, qs=qs)


def post(path: str, body: dict, qs: dict | None = None) -> dict:
    return _request("POST", path, body=body, qs=qs)


def patch(path: str, body: dict, qs: dict | None = None) -> dict:
    return _request("PATCH", path, body=body, qs=qs)


def delete(path: str, qs: dict | None = None) -> dict:
    return _request("DELETE", path, qs=qs)
