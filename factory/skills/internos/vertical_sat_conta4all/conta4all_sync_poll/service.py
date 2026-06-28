"""Paso 2 sync granular: re-auth SAT + UNA llamada a sat_cfdi_verificar (sin loop bloqueante)."""
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
_CACHE_PATH = Path(tempfile.gettempdir()) / "conta4all_sat_solicitudes.json"


class Conta4allSyncPollService:

    def ejecutar(self, context: dict) -> dict:
        rfc          = (context.get("rfc") or os.getenv("SAT_RFC", "")).strip().upper()
        cer_b64      = context.get("cer_b64") or os.getenv("SAT_EFIRMA_CER_B64", "")
        key_b64      = context.get("key_b64") or os.getenv("SAT_EFIRMA_KEY_B64", "")
        key_pwd      = context.get("key_password") or os.getenv("SAT_EFIRMA_PASSWORD", "")
        id_solicitud = (context.get("id_solicitud") or "").strip()
        managed_id   = str(context.get("managed_rfc_id") or "").strip()

        if context.get("dry_run"):
            return {"ok": True, "message": "dry_run", "data": {
                "listo": False, "esperar": True, "estado": "dry",
                "paquetes": [], "num_cfdis": 0,
            }}

        if not all([rfc, cer_b64, key_b64, key_pwd, id_solicitud]):
            return {"ok": False,
                    "error": "Faltan: rfc, cer_b64, key_b64, key_password, id_solicitud"}

        creds = {"rfc": rfc, "cer_b64": cer_b64, "key_b64": key_b64, "key_password": key_pwd}

        # Re-autenticar siempre — token SAT dura ~5 min
        r1 = self._run_sat("sat_auth", {**creds, "dry_run": False})
        if not r1.get("ok"):
            return {"ok": False, "error": f"sat_auth: {r1.get('error', '')}",
                    "data": {"paso": "sat_auth"}}
        token = r1["data"]["token"]

        # UNA sola verificación — sin loop
        r2 = self._run_sat("sat_cfdi_verificar", {
            **creds, "token": token, "id_solicitud": id_solicitud, "dry_run": False,
        })
        d = r2.get("data") or {}
        normalized = self._normalize_sat_status(id_solicitud, d, r2.get("message", ""))
        if not r2.get("ok"):
            msg = r2.get("error") or r2.get("message") or "sin detalle"
            self._update_request_state(context, {
                "id_solicitud": id_solicitud,
                "managed_rfc_id": managed_id,
                "estado": normalized["estado_solicitud"],
                "paquetes": normalized["paquetes"],
                "num_cfdis": normalized["num_cfdis"],
                "ultimo_error": msg,
            })
            if normalized["esperar"]:
                return {"ok": True, "message": msg, "data": normalized}
            return {"ok": False, "error": f"sat_cfdi_verificar: {msg}",
                    "data": {"paso": "sat_cfdi_verificar", **normalized}}

        self._update_request_state(context, {
            "id_solicitud": id_solicitud,
            "managed_rfc_id": managed_id,
            "estado": normalized["estado_solicitud"],
            "paquetes": normalized["paquetes"],
            "num_cfdis": normalized["num_cfdis"],
            "ultimo_error": "" if not normalized["error_sat"] else normalized["estado"],
        })
        if normalized["error_sat"]:
            return {"ok": False, "error": normalized["estado"], "data": normalized}
        return {
            "ok":      True,
            "message": r2.get("message", ""),
            "data":    normalized,
        }

    def _normalize_sat_status(self, id_solicitud: str, data: dict, message: str) -> dict:
        estado_num = self._estado_num(data)
        paquetes = data.get("paquetes", []) or []
        cod_sol = (
            data.get("codigo_estado_solicitud")
            or data.get("cod_solicitud")
            or data.get("codigo_estado")
            or data.get("cod_estado")
            or ""
        )
        estado_txt = self._estado_texto(estado_num, message)

        if estado_num in (0, 1, 2):
            listo, esperar, vacio, error_sat = False, True, False, False
        elif estado_num == 3:
            vacio = bool(data.get("vacio")) or str(cod_sol) in {"5003", "5004"} or not paquetes
            listo, esperar, error_sat = bool(paquetes) and not vacio, False, False
        elif estado_num in (4, 5, 6):
            listo, esperar, vacio, error_sat = False, False, False, True
        else:
            listo = bool(data.get("listo")) and bool(paquetes)
            esperar = bool(data.get("esperar")) and not listo
            vacio = bool(data.get("vacio"))
            error_sat = bool(data.get("error_sat"))

        return {
            "id_solicitud": id_solicitud,
            "estado": estado_txt,
            "estado_solicitud": estado_num,
            "codigo_estado_solicitud": cod_sol,
            "listo": listo,
            "esperar": esperar,
            "vacio": vacio,
            "error_sat": error_sat,
            "paquetes": paquetes if listo else [],
            "num_cfdis": len(paquetes) if listo else 0,
        }

    def _estado_num(self, data: dict) -> int:
        raw = data.get("estado_solicitud")
        if raw is None:
            raw = data.get("estado")
        try:
            return int(raw)
        except Exception:
            if data.get("listo"):
                return 3
            if data.get("esperar"):
                return 2
            if data.get("vacio"):
                return 3
            if data.get("error_sat"):
                return 4
            return 1

    def _estado_texto(self, estado: int, fallback: str = "") -> str:
        nombres = {
            0: "Pendiente",
            1: "Aceptada",
            2: "En proceso",
            3: "Terminada",
            4: "Error",
            5: "Rechazada",
            6: "Vencida",
        }
        base = nombres.get(estado, fallback or "Desconocido")
        return f"EstadoSolicitud={estado} ({base})" if estado in nombres else base


    def _update_request_state(self, context: dict, values: dict) -> None:
        self._update_request_state_supabase(context, values)
        self._update_request_state_cache(values)

    def _update_request_state_supabase(self, context: dict, values: dict) -> None:
        url, key = self._platform_supabase(context)
        if not url or not key or not values.get("id_solicitud"):
            return
        patch = {
            "estado": int(values.get("estado", 1)),
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
                    "estado": int(values.get("estado", row.get("estado", 1))),
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
            return {"ok": False, "error": f"{type(e).__name__}: {e}"}
        finally:
            if sys.path and sys.path[0] == str(skill_path):
                sys.path.pop(0)
