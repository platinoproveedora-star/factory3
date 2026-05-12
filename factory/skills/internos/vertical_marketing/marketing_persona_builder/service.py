"""Define buyer persona: dolores, motivadores, objeciones, lenguaje y triggers de compra."""
from __future__ import annotations
import json, os, urllib.request


class MarketingPersonaBuilderService:

    def ejecutar(self, context: dict) -> dict:
        negocio  = context.get("negocio", "").strip()
        producto = context.get("producto", "").strip()
        mercado  = context.get("mercado", "").strip()

        if not negocio:
            return {"ok": False, "error": "negocio requerido"}
        if not producto:
            return {"ok": False, "error": "producto requerido"}
        if not mercado:
            return {"ok": False, "error": "mercado requerido"}

        num        = min(int(context.get("num_personas", 2)), 5)
        contexto   = context.get("contexto", "")

        if context.get("dry_run", True):
            return {"ok": True, "data": {"dry_run": True, "negocio": negocio}}

        prompt = (
            f"Crea {num} buyer personas detalladas.\n"
            f"Negocio: {negocio}\n"
            f"Producto/Servicio: {producto}\n"
            f"Mercado: {mercado}\n"
            f"Contexto adicional: {contexto or 'ninguno'}\n\n"
            "Devuelve JSON con:\n"
            '{"personas":[{"nombre":"...","edad":"...","ocupacion":"...","ingreso":"...",'
            '"descripcion":"...","metas":[],"dolores":[],"motivadores":[],"objeciones":[],'
            '"canales_preferidos":[],"lenguaje_tipico":[],"triggers_compra":[],'
            '"frase_tipica":"...","como_convencerlo":"...","mensaje_clave":"..."}]}'
        )
        return self._haiku(prompt, "Eres un experto en marketing estratégico y segmentación de mercados. Responde SIEMPRE en JSON válido.")

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
