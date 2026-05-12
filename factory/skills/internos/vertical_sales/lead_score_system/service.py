"""Puntúa lead 0-100 según intención, canal y señales del mensaje con IA."""
from __future__ import annotations
import json, os, urllib.request

_SCHEMA = "sales"

_INTENT_BASE = {
    "agendar_cita":       90,
    "solicitud_precio":   75,
    "consulta_comercial": 60,
    "disponibilidad":     55,
    "seguimiento":        50,
    "queja":              20,
    "otro":               10,
    "spam":               0,
}

_CANAL_BONUS = {
    "web":       15,
    "whatsapp":  10,
    "telegram":   5,
    "instagram":  5,
}


class LeadScoreService:

    def ejecutar(self, context: dict) -> dict:
        lead_id    = context.get("lead_id", "").strip()
        empresa_id = context.get("empresa_id", "").strip()
        intent     = context.get("intent", "otro").strip()
        texto      = context.get("texto", "")
        canal      = context.get("canal", "telegram").strip()
        dry_run    = context.get("dry_run", True)

        if not lead_id:
            return {"ok": False, "error": "lead_id requerido"}
        if not empresa_id:
            return {"ok": False, "error": "empresa_id requerido"}

        base   = _INTENT_BASE.get(intent, 10)
        bonus  = _CANAL_BONUS.get(canal, 0)
        ajuste = self._ai_adjust(texto, intent)
        score  = min(100, max(0, base + bonus + ajuste))
        nivel  = "caliente" if score >= 70 else "tibio" if score >= 40 else "frio"

        if dry_run:
            return {"ok": True, "data": {
                "score":   score,
                "nivel":   nivel,
                "razon":   f"base={base}, canal={bonus}, ia={ajuste}",
                "dry_run": True,
            }}

        url = os.getenv("SUPABASE_URL", "").rstrip("/")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        if not url or not key:
            return {"ok": False, "error": "Faltan SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY"}

        try:
            req = urllib.request.Request(
                f"{url}/rest/v1/leads?id=eq.{lead_id}",
                data=json.dumps({"score": score}).encode(),
                headers={
                    "apikey":          key,
                    "Authorization":   f"Bearer {key}",
                    "Content-Type":    "application/json",
                    "Content-Profile": _SCHEMA,
                    "Prefer":          "return=representation",
                },
                method="PATCH",
            )
            urllib.request.urlopen(req, timeout=10)
        except Exception as e:
            return {"ok": False, "error": f"Error actualizando score: {e}"}

        return {"ok": True, "data": {
            "lead_id": lead_id,
            "score":   score,
            "nivel":   nivel,
            "razon":   f"base={base}, canal={bonus}, ia={ajuste}",
        }}

    def _ai_adjust(self, texto: str, intent: str) -> int:
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key or not texto:
            return 0
        try:
            prompt = (
                f"Analiza este mensaje de un posible cliente. Intención: {intent}.\n"
                f"Mensaje: {texto}\n\n"
                f"Dame un ajuste de score entre -20 y +20 según urgencia, claridad de necesidad y señales de compra.\n"
                f'Responde SOLO con JSON: {{"ajuste": <número>}}'
            )
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=json.dumps({
                    "model":      "claude-haiku-4-5-20251001",
                    "max_tokens": 64,
                    "messages":   [{"role": "user", "content": prompt}],
                }).encode(),
                headers={
                    "content-type":      "application/json",
                    "x-api-key":         api_key,
                    "anthropic-version": "2023-06-01",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as r:
                text = json.loads(r.read().decode())["content"][0]["text"].strip()
                if text.startswith("```"):
                    text = text.split("```")[1]
                    if text.startswith("json"): text = text[4:]
                    text = text.strip()
                return int(json.loads(text).get("ajuste", 0))
        except Exception:
            return 0
