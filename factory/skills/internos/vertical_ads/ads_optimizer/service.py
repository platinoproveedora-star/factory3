"""Recomienda pausar, escalar, duplicar o redistribuir presupuesto según performance."""
from __future__ import annotations
import json, os, urllib.request


class AdsOptimizerService:

    def ejecutar(self, context: dict) -> dict:
        campanas  = context.get("campanas") or []
        objetivo  = context.get("objetivo", "").strip()

        if not campanas:
            return {"ok": False, "error": "campanas requerido (lista de campañas con métricas)"}
        if not objetivo:
            return {"ok": False, "error": "objetivo requerido"}

        presupuesto_disponible = context.get("presupuesto_disponible", 0)
        roas_objetivo          = context.get("roas_objetivo", 2.0)
        cpl_maximo             = context.get("cpl_maximo", "")

        if context.get("dry_run", True):
            return {"ok": True, "data": {"dry_run": True, "campanas_recibidas": len(campanas)}}

        campanas_txt = json.dumps(campanas, ensure_ascii=False)
        prompt = (
            f"Optimiza el portafolio de campañas publicitarias.\n"
            f"Objetivo: {objetivo}\n"
            f"Presupuesto adicional disponible: {presupuesto_disponible}\n"
            f"ROAS objetivo: {roas_objetivo}\n"
            f"CPL máximo aceptado: {cpl_maximo or 'no definido'}\n\n"
            f"CAMPAÑAS ACTUALES:\n{campanas_txt}\n\n"
            "Clasifica cada campaña y recomienda acción específica.\n"
            "Devuelve JSON con:\n"
            '{"acciones":[{"campana":"...","accion":"pausar|escalar|duplicar|reducir|mantener|optimizar",'
            '"justificacion":"...","cambio_presupuesto_pct":0,"prioridad":"alta|media|baja"}],'
            '"redistribucion_presupuesto":[],"ganadores":[],"perdedores":[],'
            '"ahorro_estimado":"...","mejora_roas_estimada":"...","resumen":"..."}'
        )
        return self._haiku(prompt, "Eres un media buyer experto en optimización de portafolios publicitarios. Responde SIEMPRE en JSON válido.")

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
