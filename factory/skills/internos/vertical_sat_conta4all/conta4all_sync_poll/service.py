"""Paso 2 sync granular: re-auth SAT + UNA llamada a sat_cfdi_verificar (sin loop bloqueante)."""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

_VERTICAL_SAT = Path(__file__).parent.parent.parent / "vertical_sat"


class Conta4allSyncPollService:

    def ejecutar(self, context: dict) -> dict:
        rfc          = (context.get("rfc") or os.getenv("SAT_RFC", "")).strip().upper()
        cer_b64      = context.get("cer_b64") or os.getenv("SAT_EFIRMA_CER_B64", "")
        key_b64      = context.get("key_b64") or os.getenv("SAT_EFIRMA_KEY_B64", "")
        key_pwd      = context.get("key_password") or os.getenv("SAT_EFIRMA_PASSWORD", "")
        id_solicitud = (context.get("id_solicitud") or "").strip()

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
        if not r2.get("ok"):
            msg = r2.get("error") or r2.get("message") or "sin detalle"
            return {"ok": False, "error": f"sat_cfdi_verificar: {msg}",
                    "data": {"paso": "sat_cfdi_verificar"}}

        d = r2["data"]
        return {
            "ok":      True,
            "message": r2.get("message", ""),
            "data": {
                "id_solicitud":     id_solicitud,
                "estado":           d.get("estado", ""),
                "estado_solicitud": d.get("estado_solicitud"),
                "listo":            d.get("listo", False),
                "esperar":          d.get("esperar", False),
                "vacio":            d.get("vacio", False),
                "error_sat":        d.get("error_sat", False),
                "paquetes":         d.get("paquetes", []),
                "num_cfdis":        d.get("num_cfdis", 0),
            },
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
