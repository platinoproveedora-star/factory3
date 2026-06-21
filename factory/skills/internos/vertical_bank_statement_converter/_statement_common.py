from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from factory.engine import SupabaseClient

_VERTICAL_ROOT = Path(__file__).parent
_MONEY_RE = re.compile(r"\$?\s*(\d{1,3}(?:,\d{3})*\.\d{2})")


def resolve_statement_context(context: dict) -> dict:
    schema = str(context.get("schema") or context.get("supabase_schema") or "").strip()
    company_id = str(context.get("company_id") or context.get("empresa_id") or "").strip()
    project_code = str(context.get("project_code") or "").strip()
    if not schema:
        return {"ok": False, "error": "schema requerido en context"}
    if not company_id:
        return {"ok": False, "error": "company_id requerido en context"}
    return {
        "ok": True,
        "data": {
            **context,
            "schema": schema,
            "company_id": company_id,
            "empresa_id": company_id,
            "project_code": project_code,
            "module_code": "bank_statement_converter",
        },
    }


def reserve_folio(ctx: dict, prefix: str, table: str) -> dict:
    service_path = (
        Path(__file__).resolve().parent.parent
        / "vertical_erp"
        / "erp_folio_reserve"
        / "service.py"
    )
    spec = importlib.util.spec_from_file_location("_folio_service", service_path)
    if spec is None or spec.loader is None:
        return {"ok": False, "error": "no se pudo cargar erp_folio_reserve"}
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.ErpFolioReserveService().ejecutar(
        {
            **ctx,
            "prefix": prefix,
            "scope": table,
            "table": table,
            "folio_column": "folio",
            "digits": 5,
            "dry_run": False,
        }
    )


def upload_pdf_to_storage(bucket: str, storage_path: str, pdf_bytes: bytes) -> dict:
    url_base = os.getenv("SUPABASE_URL", "").rstrip("/")
    svc_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url_base or not svc_key:
        return {"ok": False, "error": "SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY requeridos"}
    object_path = urllib.parse.quote(storage_path.replace("\\", "/"), safe="/")
    url = f"{url_base}/storage/v1/object/{bucket}/{object_path}"
    req = urllib.request.Request(
        url,
        data=pdf_bytes,
        headers={
            "apikey": svc_key,
            "Authorization": f"Bearer {svc_key}",
            "Content-Type": "application/pdf",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            body = json.loads(resp.read().decode())
            return {"ok": True, "data": body}
    except urllib.error.HTTPError as exc:
        return {"ok": False, "error": f"Storage {exc.code}: {exc.read().decode()[:300]}"}
    except Exception as exc:
        return {"ok": False, "error": f"Storage error: {exc}"}


def storage_exists(bucket: str, storage_path: str) -> bool:
    url_base = os.getenv("SUPABASE_URL", "").rstrip("/")
    svc_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    object_path = urllib.parse.quote(storage_path.replace("\\", "/"), safe="/")
    url = f"{url_base}/storage/v1/object/{bucket}/{object_path}"
    req = urllib.request.Request(
        url, headers={"apikey": svc_key, "Authorization": f"Bearer {svc_key}"}, method="HEAD"
    )
    try:
        urllib.request.urlopen(req)
        return True
    except Exception:
        return False


def load_profile(bank_profile: str, profile_version: str = "v1") -> dict | None:
    path = _VERTICAL_ROOT / "profiles" / f"{bank_profile}.{profile_version}.profile.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def list_profiles() -> list[dict]:
    profiles_dir = _VERTICAL_ROOT / "profiles"
    result = []
    for p in sorted(profiles_dir.glob("*.profile.json")):
        try:
            with open(p, encoding="utf-8") as fh:
                result.append(json.load(fh))
        except Exception:
            pass
    return result


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_money(text: str) -> float | None:
    vals = _MONEY_RE.findall(text)
    if not vals:
        return None
    return float(vals[-1].replace(",", ""))


def parse_all_money(text: str) -> list[float]:
    return [float(v.replace(",", "")) for v in _MONEY_RE.findall(text)]


def build_blocks(lines: list[str], profile: dict) -> list[list[str]]:
    anchor_re = re.compile(profile["anchor_regex"])
    skip_patterns = [re.compile(p) for p in (profile.get("skip_line_patterns") or [])]
    blocks: list[list[str]] = []
    current: list[str] = []
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if any(sp.match(line) for sp in skip_patterns):
            continue
        if anchor_re.match(line):
            if current:
                blocks.append(current)
            current = [line]
        elif current:
            current.append(line)
    if current:
        blocks.append(current)
    return blocks
