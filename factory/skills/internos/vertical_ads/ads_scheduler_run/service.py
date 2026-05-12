"""Planifica lanzamientos, pausas y cambios programados de campañas con IA."""
from __future__ import annotations
import json, os, urllib.request
from datetime import datetime, timezone

_TIPOS_ACCION = {"lanzar", "pausar", "activar", "escalar", "reducir", "duplicar"}


class AdsSchedulerRunService:

    def ejecutar(self, context: dict) -> dict:
        acciones = context.get("acciones") or []
        campana  = context.get("campana", "").strip()

        if not acciones and not campana:
            return {"ok": False, "error": "acciones (lista) o campana requerido"}

        objetivo   = context.get("objetivo", "")
        condiciones = context.get("condiciones", "")
        zona_horaria = context.get("zona_horaria", "America/Mexico_City")

        if context.get("dry_run", True):
            return {"ok": True, "data": {"dry_run": True, "acciones_recibidas": len(acciones)}}

        acciones_txt = json.dumps(acciones, ensure_ascii=False) if acciones else "ninguna especificada"
        prompt = (
            f"Planifica la ejecución de cambios programados en campañas publicitarias.\n"
            f"Campaña principal: {campana or 'múltiples'}\n"
            f"Objetivo: {objetivo or 'no especificado'}\n"
            f"Zona horaria: {zona_horaria}\n"
            f"Condiciones de disparo: {condiciones or 'basado en fechas'}\n"
            f"Acciones solicitadas:\n{acciones_txt}\n\n"
            "Valida conflictos, ordena por prioridad y agrega condiciones de seguridad.\n"
            "Devuelve JSON con:\n"
            '{"plan_ejecucion":[{"orden":1,"accion":"...","campana":"...","fecha_hora":"...","condicion":"...",'
            '"impacto":"...","riesgo":"bajo|medio|alto","requiere_aprobacion":false}],'
            '"conflictos":[],"advertencias":[],"resumen":"..."}'
        )
        return self._haiku(prompt, "Eres un experto en automatización y programación de campañas publicitarias. Responde SIEMPRE en JSON válido.")

    def _haiku(self, prompt: str, system: str) -> dict:
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            return {"ok": False, "error": "ANTHROPIC_API_KEY no configurada"}
        try:
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=json.dumps({"model": "claude-haiku-4-5-20251001", "max_tokens": 2048,
                    "system": system, "messages": [{"role": "user", "content": prompt}]}).encode(),
                headers={"content-type": "application/json", "x-api-key": api_key, "anthropic-version": "2023-06-01"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=45) as r:
                raw = json.loads(r.read().decode())["content"][0]["text"].strip()
            try:
                return {"ok": True, "data": json.loads(raw)}
            except Exception:
                return {"ok": True, "data": {"raw": raw}}
        except Exception as e:
            return {"ok": False, "error": str(e)}
