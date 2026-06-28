"""Paso 3 sync granular: sat_cfdi_descargar + sat_cfdi_parser + conta4all_cfdi_store por managed_rfc_id."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

_VERTICAL_SAT = Path(__file__).parent.parent.parent / "vertical_sat"
_VERTICAL_C4A = Path(__file__).parent.parent  # vertical_sat_conta4all
_CACHE_PATH = Path(tempfile.gettempdir()) / "conta4all_sat_solicitudes.json"


class Conta4allSyncFinalizeService:

    def ejecutar(self, context: dict) -> dict:
        rfc            = (context.get("rfc") or os.getenv("SAT_RFC", "")).strip().upper()
        cer_b64        = context.get("cer_b64") or os.getenv("SAT_EFIRMA_CER_B64", "")
        key_b64        = context.get("key_b64") or os.getenv("SAT_EFIRMA_KEY_B64", "")
        key_pwd        = context.get("key_password") or os.getenv("SAT_EFIRMA_PASSWORD", "")
        managed_rfc_id = str(context.get("managed_rfc_id") or "").strip()
        tipo           = context.get("tipo", "E")
        id_solicitud   = str(context.get("id_solicitud") or "").strip()
        paquetes       = context.get("paquetes") or []

        if context.get("dry_run"):
            return {"ok": True, "message": "dry_run", "data": {"cfdis_guardados": 0, "log": []}}

        if not all([rfc, cer_b64, key_b64, key_pwd, managed_rfc_id]):
            return {"ok": False,
                    "error": "Faltan: rfc, cer_b64, key_b64, key_password, managed_rfc_id"}

        if not paquetes:
            return {"ok": False, "error": "paquetes requerido (lista de ids de paquetes SAT)"}

        creds = {"rfc": rfc, "cer_b64": cer_b64, "key_b64": key_b64, "key_password": key_pwd}
        log   = []

        r1 = self._run(_VERTICAL_SAT, "sat_auth", {**creds, "dry_run": False})
        if not r1.get("ok"):
            return {"ok": False, "error": f"sat_auth: {r1.get('error', '')}",
                    "data": {"log": log}}
        token = r1["data"]["token"]
        log.append({"paso": "sat_auth", "ok": True})

        total_guardados = 0
        for id_paquete in paquetes:
            r2 = self._run(_VERTICAL_SAT, "sat_cfdi_descargar", {
                **creds, "token": token, "id_paquete": id_paquete, "dry_run": False,
            })
            log.append({"paso": f"sat_cfdi_descargar:{id_paquete}", "ok": r2.get("ok"),
                        "msg": r2.get("message") or r2.get("error", "")})
            if not r2.get("ok"):
                continue

            xmls = r2["data"].get("xmls", [])
            r3   = self._run(_VERTICAL_SAT, "sat_cfdi_parser", {"xmls": xmls, "dry_run": False})
            log.append({"paso": "sat_cfdi_parser", "ok": r3.get("ok"),
                        "msg": r3.get("message", "")})
            if not r3.get("ok"):
                continue

            cfdis = r3["data"].get("cfdis", [])
            r4    = self._run(_VERTICAL_C4A, "conta4all_cfdi_store", {
                **context,
                "managed_rfc_id": managed_rfc_id,
                "cfdis":          cfdis,
                "tipo":           tipo,
                "dry_run":        False,
            })
            log.append({"paso": "conta4all_cfdi_store", "ok": r4.get("ok"),
                        "msg": r4.get("message") or r4.get("error", "")})
            total_guardados += r4.get("data", {}).get("insertados", 0)

        if id_solicitud:
            self._update_request_state(context, {
                "id_solicitud": id_solicitud,
                "estado": 3,
                "paquetes": paquetes,
                "num_cfdis": total_guardados,
                "ultimo_error": "",
            })

        return {
            "ok":      True,
            "message": f"{total_guardados} CFDIs guardados (tipo={tipo})",
            "data": {
                "cfdis_guardados":     total_guardados,
                "paquetes_procesados": len(paquetes),
                "log":                 log,
            },
        }

    def _update_request_state(self, context: dict, values: dict) -> None:
        self._update_request_state_supabase(context, values)
        self._update_request_state_cache(values)

    def _update_request_state_supabase(self, context: dict, values: dict) -> None:
        url, key = self._platform_supabase(context)
        if not url or not key or not values.get("id_solicitud"):
            return
        patch = {
            "estado": int(values.get("estado", 3)),
            "paquetes": values.get("paquetes", []),
            "num_cfdis": int(values.get("num_cfdis", 0) or 0),
            "ultimo_error": values.get("ultimo_error", ""),
        }
        qs = urllib.parse.urlencode({"id_solicitud": f"eq.{values['id_solicitud']}"}, safe=".")
        req = urllib.request.Request(
            f"{url}/rest/v1/sat_solicitudes?{qs}",
            data=json.dumps(patch).encode("utf-8"),
            headers={**self._platform_headers(key), "Prefer": "return=minimal"},
            method="PATCH",
        )
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                resp.read()
        except Exception:
            return

    def _update_request_state_cache(self, values: dict) -> None:
        rows = self._read_cache()
        changed = False
        for row in rows:
            if row.get("id_solicitud") == values.get("id_solicitud"):
                row.update({
                    "estado": int(values.get("estado", row.get("estado", 3))),
                    "paquetes": values.get("paquetes", row.get("paquetes", [])),
                    "num_cfdis": int(values.get("num_cfdis", row.get("num_cfdis", 0)) or 0),
                    "ultimo_error": values.get("ultimo_error", ""),
                })
                changed = True
        if changed:
            self._write_cache(rows)

    def _read_cache(self) -> list[dict]:
        try:
            return json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return []

    def _write_cache(self, rows: list[dict]) -> None:
        try:
            _CACHE_PATH.write_text(json.dumps(rows[:100]), encoding="utf-8")
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

    def _run(self, vertical_path: Path, skill_name: str, ctx: dict) -> dict:
        skill_path  = vertical_path / skill_name
        entrypoint  = skill_path / "skill.py"
        if not entrypoint.exists():
            return {"ok": False, "error": f"skill no encontrado: {skill_name}"}
        module_name = f"_c4a_{skill_name}"
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
