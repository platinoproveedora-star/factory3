"""Orquestador SAT: auth → solicitud → verificar(poll) → descargar → parsear → guardar."""
from __future__ import annotations

import importlib.util
import os
import sys
import time
from pathlib import Path

_VERTICAL = Path(__file__).parent.parent  # factory/skills/internos/vertical_sat/

_POLL_MAX     = 60
_POLL_SLEEP   = 15  # segundos entre verificaciones


class SatCfdiSyncService:

    def ejecutar(self, context: dict) -> dict:
        empresa_id   = context.get("empresa_id")   or os.getenv("EMPRESA_ID", "")
        rfc          = context.get("rfc")          or os.getenv("SAT_RFC", "")
        cer_b64      = context.get("cer_b64")      or os.getenv("SAT_EFIRMA_CER_B64", "")
        key_b64      = context.get("key_b64")      or os.getenv("SAT_EFIRMA_KEY_B64", "")
        key_pwd      = context.get("key_password") or os.getenv("SAT_EFIRMA_PASSWORD", "")
        fecha_inicio = context.get("fecha_inicio", "")
        fecha_fin    = context.get("fecha_fin", "")
        tipo         = context.get("tipo", "E")
        tipo_comp    = context.get("tipo_comprobante", "")
        id_solicitud = str(context.get("id_solicitud") or "").strip()
        tipo_sol     = context.get("tipo_solicitud") or context.get("request_type") or "CFDI"
        rfc_match    = context.get("rfc_contraparte") or context.get("rfc_match") or ""

        if context.get("dry_run"):
            return {"ok": True, "message": "dry_run", "data": {"cfdis_guardados": 0, "log": []}}

        if not all([empresa_id, rfc, cer_b64, key_b64, key_pwd]):
            return {"ok": False, "error": "Faltan: empresa_id/rfc/efirma creds"}
        if not id_solicitud and not all([fecha_inicio, fecha_fin]):
            return {"ok": False, "error": "Faltan: fecha_inicio/fecha_fin o id_solicitud existente"}

        creds = {"rfc": rfc, "cer_b64": cer_b64, "key_b64": key_b64, "key_password": key_pwd}
        log   = []

        # 1 — Autenticar
        r1 = self._run("sat_auth", {**creds, "dry_run": False})
        log.append({"paso": "sat_auth", "ok": r1.get("ok"), "msg": r1.get("message", "")})
        if not r1.get("ok"):
            return {"ok": False, "error": r1.get("error"), "data": {"log": log}}
        token = r1["data"]["token"]

        # 2 — Solicitar descarga o reusar una solicitud SAT ya aceptada.
        if id_solicitud:
            log.append({"paso": "sat_cfdi_solicitud", "ok": True, "msg": f"Reusando solicitud SAT: {id_solicitud}"})
        else:
            r2 = self._run("sat_cfdi_solicitud", {
                **creds, "token": token,
                "fecha_inicio": fecha_inicio, "fecha_fin": fecha_fin,
                "tipo": tipo, "tipo_comprobante": tipo_comp,
                "tipo_solicitud": tipo_sol, "rfc_contraparte": rfc_match,
                "dry_run": False,
            })
            log.append({"paso": "sat_cfdi_solicitud", "ok": r2.get("ok"), "msg": r2.get("message", "")})
            if not r2.get("ok"):
                return {"ok": False, "error": r2.get("error"), "data": {"log": log}}
            id_solicitud = r2["data"]["id_solicitud"]

        # 3 — Verificar con polling
        paquetes = []
        for intento in range(_POLL_MAX):
            time.sleep(_POLL_SLEEP if intento > 0 else 3)
            r3 = self._run("sat_cfdi_verificar", {
                **creds, "token": token, "id_solicitud": id_solicitud, "dry_run": False,
            })
            estado = r3.get("data", {})
            log.append({"paso": f"sat_cfdi_verificar#{intento+1}", "ok": r3.get("ok"),
                        "msg": r3.get("message", "")})
            if not r3.get("ok"):
                return {"ok": False, "error": r3.get("error"), "data": {"log": log}}
            if estado.get("listo"):
                paquetes = estado.get("paquetes", [])
                break
            if estado.get("vacio"):
                return {"ok": True, "message": "SAT: sin CFDIs en ese rango",
                        "data": {"cfdis_guardados": 0, "log": log}}
            if not estado.get("esperar"):
                return {"ok": False, "error": f"Estado inesperado: {estado.get('cod_estado')}",
                        "data": {"log": log}}

        if not paquetes:
            return {
                "ok": False,
                "error": f"Timeout esperando paquetes SAT para id_solicitud={id_solicitud}",
                "data": {"id_solicitud": id_solicitud, "log": log},
            }

        # 4 — Descargar + parsear + guardar
        total_guardados = 0
        for id_paquete in paquetes:
            r4 = self._run("sat_cfdi_descargar", {
                **creds, "token": token, "id_paquete": id_paquete, "dry_run": False,
            })
            log.append({"paso": f"sat_cfdi_descargar:{id_paquete}", "ok": r4.get("ok"),
                        "msg": r4.get("message", "")})
            if not r4.get("ok"):
                continue

            xmls = r4["data"].get("xmls", [])
            r5   = self._run("sat_cfdi_parser", {"xmls": xmls, "dry_run": False})
            log.append({"paso": "sat_cfdi_parser", "ok": r5.get("ok"), "msg": r5.get("message", "")})
            if not r5.get("ok"):
                continue

            cfdis = r5["data"].get("cfdis", [])
            r6    = self._run("sat_cfdi_store", {
                "empresa_id": empresa_id, "cfdis": cfdis, "tipo": tipo,
                "rfc_propietario": rfc, "dry_run": False,
            })
            log.append({"paso": "sat_cfdi_store", "ok": r6.get("ok"), "msg": r6.get("message", "")})
            total_guardados += r6.get("data", {}).get("insertados", 0)

        return {
            "ok":      True,
            "message": f"{total_guardados} CFDIs guardados ({tipo}, {fecha_inicio}→{fecha_fin})",
            "data": {
                "cfdis_guardados": total_guardados,
                "paquetes":        len(paquetes),
                "id_solicitud":    id_solicitud,
                "log":             log,
            },
        }

    def _run(self, skill_name: str, ctx: dict) -> dict:
        skill_path  = _VERTICAL / skill_name
        entrypoint  = skill_path / "skill.py"
        if not entrypoint.exists():
            return {"ok": False, "error": f"skill no encontrado: {skill_name}"}
        module_name = f"_sat_{skill_name.replace('/', '_')}"
        spec        = importlib.util.spec_from_file_location(module_name, entrypoint)
        if not spec or not spec.loader:
            return {"ok": False, "error": f"error cargando: {skill_name}"}
        module = importlib.util.module_from_spec(spec)
        sys.path.insert(0, str(skill_path))
        # Limpiar módulos de nombre genérico para evitar colisión de caché entre skills
        for _k in [k for k in sys.modules if k in ("service", "skill")]:
            del sys.modules[_k]
        try:
            spec.loader.exec_module(module)
            return module.run(ctx)
        except Exception as e:
            return {"ok": False, "error": str(e)}
        finally:
            if sys.path and sys.path[0] == str(skill_path):
                sys.path.pop(0)
