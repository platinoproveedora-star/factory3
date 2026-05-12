"""Distribuye presupuesto por canal, campaña, conjunto, etapa de funnel y prueba con IA."""
from __future__ import annotations
import json, os, urllib.request

_OBJETIVOS = {"trafico", "conversiones", "leads", "alcance", "engagement", "ventas", "branding"}


class AdsBudgetPlannerService:

    def ejecutar(self, context: dict) -> dict:
        presupuesto = context.get("presupuesto_total")
        objetivo    = context.get("objetivo", "").strip()
        canales     = context.get("canales") or []

        if presupuesto is None:
            return {"ok": False, "error": "presupuesto_total requerido"}
        if not objetivo:
            return {"ok": False, "error": "objetivo requerido"}
        if not canales:
            return {"ok": False, "error": "canales requerido (lista: meta, google, tiktok, etc.)"}

        duracion    = int(context.get("duracion_dias", 30))
        etapa       = context.get("etapa_funnel", "full")
        pct_prueba  = float(context.get("pct_prueba", 20))
        moneda      = context.get("moneda", "MXN")

        if context.get("dry_run", True):
            return {"ok": True, "data": {"dry_run": True, "presupuesto_total": presupuesto}}

        prompt = (
            f"Distribuye un presupuesto publicitario de manera estratégica.\n"
            f"Presupuesto total: {presupuesto} {moneda}\n"
            f"Objetivo: {objetivo}\n"
            f"Canales disponibles: {', '.join(canales)}\n"
            f"Duración: {duracion} días\n"
            f"Etapa del funnel: {etapa}\n"
            f"% para pruebas A/B: {pct_prueba}%\n\n"
            "Distribuye considerando: ROI esperado por canal, etapa del funnel, fase de aprendizaje y reserva para escalar.\n"
            "Devuelve JSON con:\n"
            '{"resumen":{"total":"...","diario":"...","moneda":"..."},'
            '"por_canal":[{"canal":"...","presupuesto":"...","pct":0,"campanas":0,"justificacion":"..."}],'
            '"por_etapa":[{"etapa":"tof|mof|bof","presupuesto":"...","pct":0}],'
            '"reserva_pruebas":{"monto":"...","uso":"..."},'
            '"semana_1":{"presupuesto":"...","objetivo":"aprendizaje"},'
            '"recomendaciones":[]}'
        )
        return self._haiku(prompt, "Eres un media buyer senior especialista en distribución de presupuesto publicitario. Responde SIEMPRE en JSON válido.")

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
