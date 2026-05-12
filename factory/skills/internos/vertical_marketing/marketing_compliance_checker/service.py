"""Revisa claims, promesas sensibles y riesgos de política publicitaria por plataforma."""
from __future__ import annotations
import json, os, urllib.request

_PLATAFORMAS = {"meta", "google", "tiktok", "linkedin", "twitter", "general"}


class MarketingComplianceCheckerService:

    def ejecutar(self, context: dict) -> dict:
        copy       = context.get("copy", "").strip()
        plataforma = context.get("plataforma", "meta").strip()

        if not copy:
            return {"ok": False, "error": "copy requerido"}
        if plataforma not in _PLATAFORMAS:
            return {"ok": False, "error": f"plataforma inválida — válidas: {', '.join(_PLATAFORMAS)}"}

        industria = context.get("industria", "general")
        imagen    = context.get("descripcion_imagen", "")

        if context.get("dry_run", True):
            return {"ok": True, "data": {"dry_run": True, "plataforma": plataforma}}

        politicas = {
            "meta":    "No claims de resultados garantizados, no antes/después en salud/fitness, no lenguaje discriminatorio, no urgencia falsa, restricciones en finanzas/salud/política",
            "google":  "No claims engañosos, no clickbait, no contenido de odio, restricciones en pharma/alcohol/juegos",
            "tiktok":  "No claims médicos, no contenido para menores, no productos regulados sin aprobación",
            "linkedin": "Contenido profesional, no spam, no claims exagerados de resultados",
            "twitter": "No contenido engañoso, restricciones en crypto/salud",
            "general": "FTC guidelines: claims verídicos, testimonios reales, disclosure de afiliados",
        }
        prompt = (
            f"Revisa este copy publicitario para cumplimiento de políticas.\n\n"
            f"COPY:\n{copy}\n\n"
            f"Plataforma: {plataforma}\n"
            f"Industria: {industria}\n"
            f"Descripción imagen (si aplica): {imagen or 'no proporcionada'}\n"
            f"Políticas relevantes: {politicas.get(plataforma, '')}\n\n"
            "Identifica: claims problemáticos, promesas no verificables, lenguaje prohibido, riesgos de rechazo.\n"
            "Devuelve JSON con:\n"
            '{"aprobado":true|false,"score_riesgo":0-100,"nivel_riesgo":"bajo|medio|alto|critico",'
            '"claims_problematicos":[],"palabras_sensibles":[],"recomendaciones":[],'
            '"version_corregida":"...","razon_rechazo_probable":"..."}'
        )
        return self._haiku(prompt, "Eres un experto en políticas publicitarias y compliance de plataformas digitales. Responde SIEMPRE en JSON válido.")

    def _haiku(self, prompt: str, system: str) -> dict:
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            return {"ok": False, "error": "ANTHROPIC_API_KEY no configurada"}
        try:
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=json.dumps({
                    "model": "claude-haiku-4-5-20251001", "max_tokens": 1024,
                    "system": system, "messages": [{"role": "user", "content": prompt}],
                }).encode(),
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
