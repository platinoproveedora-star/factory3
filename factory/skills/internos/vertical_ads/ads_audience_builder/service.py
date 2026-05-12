"""Define audiencia abstracta: geografía, edad, intereses, exclusiones e intención."""
from __future__ import annotations
import json, os, urllib.request

_TIPOS = {"fria", "caliente", "retargeting", "lookalike", "mixta"}
_PLATAFORMAS = {"meta", "google", "tiktok", "linkedin", "twitter", "general"}


class AdsAudienceBuilderService:

    def ejecutar(self, context: dict) -> dict:
        producto   = context.get("producto", "").strip()
        objetivo   = context.get("objetivo", "").strip()
        tipo       = context.get("tipo_audiencia", "fria").strip()
        plataforma = context.get("plataforma", "meta").strip()

        if not producto:
            return {"ok": False, "error": "producto requerido"}
        if not objetivo:
            return {"ok": False, "error": "objetivo requerido"}
        if tipo not in _TIPOS:
            return {"ok": False, "error": f"tipo_audiencia inválido — válidos: {', '.join(_TIPOS)}"}
        if plataforma not in _PLATAFORMAS:
            return {"ok": False, "error": f"plataforma inválida — válidas: {', '.join(_PLATAFORMAS)}"}

        mercado   = context.get("mercado", "México")
        personas  = context.get("buyer_personas", "")
        exclusiones = context.get("exclusiones", "")

        if context.get("dry_run", True):
            return {"ok": True, "data": {"dry_run": True, "tipo": tipo, "plataforma": plataforma}}

        prompt = (
            f"Define una audiencia publicitaria estructurada para {plataforma}.\n"
            f"Producto/Servicio: {producto}\n"
            f"Objetivo: {objetivo}\n"
            f"Tipo de audiencia: {tipo}\n"
            f"Mercado/Geografía: {mercado}\n"
            f"Buyer personas de referencia: {personas or 'no especificado'}\n"
            f"Exclusiones solicitadas: {exclusiones or 'ninguna'}\n\n"
            "Devuelve JSON con:\n"
            '{"nombre_audiencia":"...","tipo":"...","plataforma":"...",'
            '"geografia":{"paises":[],"ciudades":[],"radio_km":null},'
            '"demograficos":{"edad_min":0,"edad_max":0,"genero":"todos|hombres|mujeres","idiomas":[]},'
            '"intereses":[],"comportamientos":[],"exclusiones":[],'
            '"intencion_compra":[],"tamano_estimado":"...","cpm_estimado":"...",'
            '"notas_plataforma":"...","recomendaciones":[]}'
        )
        return self._haiku(prompt, "Eres un experto en targeting y segmentación de audiencias publicitarias. Responde SIEMPRE en JSON válido.")

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
