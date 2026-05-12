"""Genera ángulos de venta por dolor, deseo, urgencia, autoridad y prueba social."""
from __future__ import annotations
import json, os, urllib.request

_TIPOS_ANGULO = {"dolor", "deseo", "urgencia", "autoridad", "prueba_social", "curiosidad", "todos"}


class MarketingAngleGeneratorService:

    def ejecutar(self, context: dict) -> dict:
        producto  = context.get("producto", "").strip()
        audiencia = context.get("audiencia", "").strip()
        if not producto:
            return {"ok": False, "error": "producto requerido"}
        if not audiencia:
            return {"ok": False, "error": "audiencia requerido"}

        tipo_angulo = context.get("tipo_angulo", "todos").strip()
        cantidad    = int(context.get("cantidad", 3))
        contexto    = context.get("contexto", "")

        if tipo_angulo not in _TIPOS_ANGULO:
            return {"ok": False, "error": f"tipo_angulo inválido — válidos: {', '.join(_TIPOS_ANGULO)}"}

        if context.get("dry_run", True):
            return {"ok": True, "data": {"dry_run": True, "producto": producto}}

        tipos_desc = {
            "dolor":        "apunta al problema urgente que el cliente quiere resolver",
            "deseo":        "apunta al resultado o transformación que el cliente quiere lograr",
            "urgencia":     "crea presión de tiempo o escasez real",
            "autoridad":    "usa credenciales, resultados o prueba de expertise",
            "prueba_social": "usa testimonios, números de clientes o casos de éxito",
            "curiosidad":   "genera intriga o pregunta irresistible",
        }
        if tipo_angulo == "todos":
            tipos_a_generar = list(tipos_desc.keys())
        else:
            tipos_a_generar = [tipo_angulo]

        prompt = (
            f"Genera ángulos de venta para:\n"
            f"Producto/Servicio: {producto}\n"
            f"Audiencia: {audiencia}\n"
            f"Contexto adicional: {contexto or 'ninguno'}\n"
            f"Tipos a generar: {', '.join(tipos_a_generar)}\n"
            f"Cantidad por tipo: {cantidad}\n\n"
            "Para cada tipo genera el número indicado de ángulos.\n"
            "Devuelve JSON con:\n"
            '{"angulos":[{"tipo":"dolor|deseo|urgencia|autoridad|prueba_social|curiosidad",'
            '"angulo":"...","hook_ejemplo":"...","por_que_funciona":"..."}]}'
        )
        return self._haiku(prompt, "Eres un experto en psicología del consumidor y copywriting persuasivo. Responde SIEMPRE en JSON válido.")

    def _haiku(self, prompt: str, system: str) -> dict:
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            return {"ok": False, "error": "ANTHROPIC_API_KEY no configurada"}
        try:
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=json.dumps({
                    "model": "claude-haiku-4-5-20251001", "max_tokens": 2048,
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
