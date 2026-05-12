"""Crea solicitud de aprobación humana antes de publicar o gastar presupuesto."""
from __future__ import annotations
from datetime import datetime, timezone

_ACCIONES = {"lanzar_campana", "pausar_campana", "escalar_presupuesto", "publicar_ad", "modificar_audiencia"}
_NIVELES  = {"bajo": 1000, "medio": 5000, "alto": 20000, "critico": 999999}


class AdsApprovalQueueCreateService:

    def ejecutar(self, context: dict) -> dict:
        tipo_accion  = context.get("tipo_accion", "").strip()
        campana      = context.get("campana", "").strip()
        responsable  = context.get("responsable", "").strip()
        empresa_id   = context.get("empresa_id", "").strip()

        if not tipo_accion or tipo_accion not in _ACCIONES:
            return {"ok": False, "error": f"tipo_accion requerido — válidos: {', '.join(_ACCIONES)}"}
        if not campana:
            return {"ok": False, "error": "campana requerido"}
        if not responsable:
            return {"ok": False, "error": "responsable requerido (email o nombre del aprobador)"}

        presupuesto   = float(context.get("presupuesto", 0))
        descripcion   = context.get("descripcion", "")
        datos_adjuntos = context.get("datos", {})

        nivel = "bajo"
        for lvl, umbral in _NIVELES.items():
            if presupuesto <= umbral:
                nivel = lvl
                break

        approval_id = f"APR-{int(datetime.now(timezone.utc).timestamp())}"
        payload = {
            "approval_id":    approval_id,
            "tipo_accion":    tipo_accion,
            "campana":        campana,
            "empresa_id":     empresa_id or "no_especificada",
            "presupuesto":    presupuesto,
            "nivel_riesgo":   nivel,
            "responsable":    responsable,
            "descripcion":    descripcion,
            "datos":          datos_adjuntos,
            "estado":         "pendiente",
            "creado_en":      datetime.now(timezone.utc).isoformat(),
            "expira_en":      None,
            "instrucciones":  f"Revisar y aprobar/rechazar {tipo_accion} para campaña '{campana}'. Presupuesto: {presupuesto}.",
        }

        return {"ok": True, "data": {
            "approval_id": approval_id,
            "nivel_riesgo": nivel,
            "estado":       "pendiente",
            "payload":      payload,
            "mensaje":      f"Solicitud {approval_id} creada. Pendiente de aprobación por {responsable}.",
        }}
