"""Genera reporte operativo multicanal de inversión, métricas y acciones recomendadas."""
from __future__ import annotations
import json, os, urllib.request


class AdsReportGeneratorService:

    def ejecutar(self, context: dict) -> dict:
        campanas  = context.get("campanas") or []
        periodo   = context.get("periodo", "").strip()
        objetivo  = context.get("objetivo", "").strip()

        if not campanas:
            return {"ok": False, "error": "campanas requerido (lista con métricas por campaña)"}
        if not objetivo:
            return {"ok": False, "error": "objetivo requerido"}

        presupuesto_total = context.get("presupuesto_total", "")
        audiencia         = context.get("audiencia", "")
        canales           = context.get("canales") or []

        if context.get("dry_run", True):
            return {"ok": True, "data": {"dry_run": True, "campanas": len(campanas)}}

        campanas_txt = json.dumps(campanas, ensure_ascii=False)
        prompt = (
            f"Genera un reporte operativo de campañas publicitarias multicanal.\n"
            f"Período: {periodo or 'no especificado'}\n"
            f"Objetivo: {objetivo}\n"
            f"Presupuesto total invertido: {presupuesto_total or 'no especificado'}\n"
            f"Canales: {', '.join(canales) if canales else 'varios'}\n"
            f"Audiencia: {audiencia or 'no especificada'}\n\n"
            f"CAMPAÑAS:\n{campanas_txt}\n\n"
            "Devuelve JSON con:\n"
            '{"resumen_ejecutivo":"...","periodo":"...","inversion_total":"...",'
            '"kpis_globales":{"impresiones":0,"clics":0,"conversiones":0,"ctr_promedio":"...","cpc_promedio":"...","roas":"..."},'
            '"por_canal":[{"canal":"...","inversion":"...","conversiones":0,"roas":"...","evaluacion":"..."}],'
            '"mejores_campanas":[],"peores_campanas":[],"aprendizajes":[],'
            '"acciones_inmediatas":[],"proximos_pasos":[],"score_general":0-100}'
        )
        return self._haiku(prompt, "Eres un analista senior de medios digitales especialista en reportes multicanal. Responde SIEMPRE en JSON válido.")

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
