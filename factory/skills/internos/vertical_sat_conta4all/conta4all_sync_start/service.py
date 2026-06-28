"""Paso 1 sync granular: sat_auth + sat_cfdi_solicitud → id_solicitud. Sin polling bloqueante."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

_VERTICAL_SAT = Path(__file__).parent.parent.parent / "vertical_sat"
_CACHE_PATH = Path(tempfile.gettempdir()) / "conta4all_sat_solicitudes.json"
_ACTIVE_ESTADOS = {0, 1, 2, 3}


class Conta4allSyncStartService:

    def ejecutar(self, context: dict) -> dict:
        rfc          = (context.get("rfc") or os.getenv("SAT_RFC", "")).strip().upper()
        cer_b64      = context.get("cer_b64") or os.getenv("SAT_EFIRMA_CER_B64", "")
        key_b64      = context.get("key_b64") or os.getenv("SAT_EFIRMA_KEY_B64", "")
        key_pwd      = context.get("key_password") or os.getenv("SAT_EFIRMA_PASSWORD", "")
        fecha_inicio = (context.get("fecha_inicio") or "").strip()
        fecha_fin    = (context.get("fecha_fin") or "").strip()
        tipo         = context.get("tipo", "E")
        tipo_sol     = context.get("tipo_solicitud", "CFDI")
        tipo_comp    = context.get("tipo_comprobante", "")
        rfc_cp       = (context.get("rfc_contraparte", "") or "").strip().upper()
        managed_id   = str(context.get("managed_rfc_id") or "").strip()

        if tipo not in ("E", "R"):
            return {"ok": False, "error": "tipo debe ser E o R. El SAT no acepta 'ambos' en una sola solicitud."}

        if context.get("dry_run"):
            return {"ok": True, "message": "dry_run", "data": {"id_solicitud": "DRY-RUN"}}

        if not all([rfc, cer_b64, key_b64, key_pwd, fecha_inicio, fecha_fin]):
            return {"ok": False,
                    "error": "Faltan: rfc, cer_b64, key_b64, key_password, fecha_inicio, fecha_fin"}

        creds = {"rfc": rfc, "cer_b64": cer_b64, "key_b64": key_b64, "key_password": key_pwd}
        base_request = {
            "managed_rfc_id": managed_id,
            "rfc": rfc,
            "tipo": tipo,
            "tipo_solicitud": tipo_sol,
            "tipo_comprobante": tipo_comp,
            "rfc_contraparte": rfc_cp,
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
        }

        existing = self._find_active_request(context, base_request)
        if existing:
            id_existing = existing.get("id_solicitud", "")
            return {
                "ok": True,
                "message": f"Reusando solicitud SAT activa: {id_existing}",
                "data": {
                    **base_request,
                    "id_solicitud": id_existing,
                    "reused": True,
                    "estado": existing.get("estado", 1),
                    "paquetes": existing.get("paquetes", []),
                },
            }

        r1 = self._run_sat("sat_auth", {**creds, "dry_run": False})
        if not r1.get("ok"):
            return {"ok": False, "error": f"sat_auth: {r1.get('error', '')}",
                    "data": {"paso": "sat_auth"}}
        token = r1["data"]["token"]

        r2 = self._run_sat("sat_cfdi_solicitud", {
            **creds,
            "token":            token,
            "fecha_inicio":     fecha_inicio,
            "fecha_fin":        fecha_fin,
            "tipo":             tipo,
            "tipo_comprobante": tipo_comp,
            "tipo_solicitud":   tipo_sol,
            "rfc_contraparte":  rfc_cp,
            "dry_run":          False,
        })
        if not r2.get("ok"):
            return {"ok": False, "error": f"sat_cfdi_solicitud: {r2.get('error', '')}",
                    "data": {"paso": "sat_cfdi_solicitud"}}

        id_solicitud = r2["data"]["id_solicitud"]
        self._save_request(context, {**base_request, "id_solicitud": id_solicitud, "estado": 1, "paquetes": []})
        return {
            "ok":      True,
            "message": f"Solicitud creada: {id_solicitud}",
            "data": {
                "id_solicitud": id_solicitud,
                "tipo":         tipo,
                "fecha_inicio": fecha_inicio,
                "fecha_fin":    fecha_fin,
                "reused":       False,
            },
        }

    def _find_active_request(self, context: dict, request_data: dict) -> dict | None:
        row = self._find_active_request_supabase(context, request_data)
        if row:
            return row
        return self._find_active_request_cache(request_data)

    def _find_active_request_supabase(self, context: dict, request_data: dict) -> dict | None:
        url, key = self._platform_supabase(context)
        if not url or not key:
            return None

        filters = {
            "managed_rfc_id": request_data.get("managed_rfc_id"),
            "rfc": request_data.get("rfc"),
            "tipo": request_data.get("tipo"),
            "tipo_solicitud": request_data.get("tipo_solicitud"),
            "tipo_comprobante": request_data.get("tipo_comprobante"),
            "rfc_contraparte": request_data.get("rfc_contraparte"),
            "fecha_inicio": request_data.get("fecha_inicio"),
            "fecha_fin": request_data.get("fecha_fin"),
        }
        params = [
            ("select", "id_solicitud,estado,paquetes,updated_at"),
            ("estado", "in.(0,1,2,3)"),
            ("order", "updated_at.desc"),
            ("limit", "1"),
        ]
        for name, value in filters.items():
            if value:
                params.append((name, f"eq.{value}"))
        qs = urllib.parse.urlencode(params, safe="(),.")
        req = urllib.request.Request(
            f"{url}/rest/v1/sat_solicitudes?{qs}",
            headers={**self._platform_headers(key), "Accept": "application/json"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                rows = json.loads(resp.read().decode("utf-8"))
        except Exception:
            return None
        if not rows:
            return None
        row = rows[0]
        if isinstance(row.get("paquetes"), str):
            try:
                row["paquetes"] = json.loads(row["paquetes"])
            except Exception:
                row["paquetes"] = []
        return row

    def _find_active_request_cache(self, request_data: dict) -> dict | None:
        rows = self._read_cache()
        now = time.time()
        best = None
        for row in rows:
            if now - float(row.get("created_ts", 0)) > 6 * 60 * 60:
                continue
            if int(row.get("estado", 1)) not in _ACTIVE_ESTADOS:
                continue
            if all(str(row.get(k, "")) == str(request_data.get(k, "")) for k in (
                "managed_rfc_id", "rfc", "tipo", "tipo_solicitud", "tipo_comprobante",
                "rfc_contraparte", "fecha_inicio", "fecha_fin"
            )):
                if best is None or float(row.get("created_ts", 0)) > float(best.get("created_ts", 0)):
                    best = row
        return best

    def _save_request(self, context: dict, request_data: dict) -> None:
        self._save_request_supabase(context, request_data)
        self._save_request_cache(request_data)

    def _save_request_supabase(self, context: dict, request_data: dict) -> None:
        url, key = self._platform_supabase(context)
        if not url or not key:
            return
        row = {
            "managed_rfc_id": request_data.get("managed_rfc_id") or None,
            "rfc": request_data.get("rfc"),
            "id_solicitud": request_data.get("id_solicitud"),
            "tipo": request_data.get("tipo"),
            "tipo_solicitud": request_data.get("tipo_solicitud") or "CFDI",
            "tipo_comprobante": request_data.get("tipo_comprobante") or "",
            "rfc_contraparte": request_data.get("rfc_contraparte") or "",
            "fecha_inicio": request_data.get("fecha_inicio"),
            "fecha_fin": request_data.get("fecha_fin"),
            "estado": int(request_data.get("estado", 1)),
            "paquetes": request_data.get("paquetes", []),
            "num_cfdis": int(request_data.get("num_cfdis", 0)),
        }
        req = urllib.request.Request(
            f"{url}/rest/v1/sat_solicitudes?on_conflict=id_solicitud",
            data=json.dumps(row).encode("utf-8"),
            headers={**self._platform_headers(key), "Prefer": "resolution=merge-duplicates,return=minimal"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                resp.read()
        except Exception:
            return

    def _save_request_cache(self, request_data: dict) -> None:
        rows = [
            row for row in self._read_cache()
            if row.get("id_solicitud") != request_data.get("id_solicitud")
        ]
        rows.insert(0, {**request_data, "created_ts": time.time()})
        self._write_cache(rows[:100])

    def _read_cache(self) -> list[dict]:
        try:
            return json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return []

    def _write_cache(self, rows: list[dict]) -> None:
        try:
            _CACHE_PATH.write_text(json.dumps(rows), encoding="utf-8")
        except Exception:
            pass

    def _platform_supabase(self, context: dict) -> tuple[str, str]:
        url = (context.get("platform_supabase_url") or os.getenv("PLATFORM_SUPABASE_URL", "")).rstrip("/")
        key = context.get("platform_supabase_service_role_key") or os.getenv("PLATFORM_SUPABASE_SERVICE_ROLE_KEY", "")
        return url, key

    def _platform_headers(self, key: str) -> dict:
        return {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Content-Profile": "conta4all",
            "Accept-Profile": "conta4all",
            "User-Agent": "FactoryFactory/0.1 (+https://github.com/)",
        }

    def _run_sat(self, skill_name: str, ctx: dict) -> dict:
        skill_path  = _VERTICAL_SAT / skill_name
        entrypoint  = skill_path / "skill.py"
        if not entrypoint.exists():
            return {"ok": False, "error": f"sat skill no encontrado: {skill_name}"}
        module_name = f"_sat_{skill_name}"
        spec        = importlib.util.spec_from_file_location(module_name, entrypoint)
        if not spec or not spec.loader:
            return {"ok": False, "error": f"error cargando: {skill_name}"}
        module = importlib.util.module_from_spec(spec)
        sys.path.insert(0, str(skill_path))
        for k in [k for k in sys.modules if k in ("service", "skill")]:
            del sys.modules[k]
        try:
            spec.loader.exec_module(module)
            return module.run(ctx)
        except Exception as e:
            return {"ok": False, "error": str(e)}
        finally:
            if sys.path and sys.path[0] == str(skill_path):
                sys.path.pop(0)
