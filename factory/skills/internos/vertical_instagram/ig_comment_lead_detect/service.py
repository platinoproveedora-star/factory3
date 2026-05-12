from __future__ import annotations
import json, os, urllib.request
from pathlib import Path


_MODEL = "claude-haiku-4-5-20251001"
_INTENT_MAP = {
    "compra": "solicitud_precio",
    "info": "consulta_comercial",
    "curiosidad": "consulta_comercial",
    "soporte": "queja",
    "spam": "spam",
    "otro": "otro",
}
_PROMPT = """Analiza este comentario de Instagram y detecta si hay intención comercial o de compra.

Post contexto: {post_context}
Comentario: {comment_text}

Responde SOLO con JSON válido, sin texto extra:
{{
  "es_lead": true/false,
  "intent": "compra|info|curiosidad|soporte|spam|otro",
  "score": 1-10,
  "respuesta_sugerida": "respuesta natural de 1-2 líneas para el comentario",
  "accion_sugerida": "dm|ignorar|responder_publico",
  "resumen": "una línea sobre el interés"
}}"""


def _runner():
    from factory.engine import SkillLoader, SkillRunner
    root = Path(__file__).parent.parent.parent
    ext_root = root.parent / "externos"
    ext_root.mkdir(parents=True, exist_ok=True)
    loader = SkillLoader(
        internal_root=root,
        external_root=ext_root,
        extra_roots={"meta": root.parent / "meta", "eval": root.parent / "eval"},
    )
    return SkillRunner(loader)


def _run(name: str, ctx: dict) -> dict:
    return _runner().run(name, ctx, source="internos")


class IgCommentLeadDetectService:

    def ejecutar(self, context: dict) -> dict:
        comment_text = (context.get("comment_text") or context.get("texto") or "").strip()
        commenter_ig_id = (context.get("commenter_ig_id") or "").strip()
        post_id = (context.get("post_id") or "").strip()
        empresa_id = (context.get("empresa_id") or "").strip()
        post_context = (context.get("post_context") or "publicación de Instagram").strip()
        dry_run = context.get("dry_run", True)

        if not comment_text:
            return {"ok": False, "error": "comment_text requerido"}
        if not empresa_id:
            return {"ok": False, "error": "empresa_id requerido"}

        clasificacion = self._clasificar(comment_text, post_context)
        if not clasificacion.get("ok"):
            return clasificacion

        datos = clasificacion["data"]

        sales_intent = _INTENT_MAP.get(str(datos.get("intent", "otro")).strip(), "otro")
        sales_context = {
            "canal":      "instagram_comment",
            "user_id":    commenter_ig_id,
            "chat_id":    post_id or commenter_ig_id,
            "texto":      comment_text,
            "empresa_id": empresa_id,
            "intent":     sales_intent,
            "dry_run":    dry_run,
            "raw_payload": {
                "origen":     "ig_comment_lead_detect",
                "comment_id": context.get("comment_id"),
                "post_id":    post_id,
                "score_ig":   datos.get("score"),
                "resumen":    datos.get("resumen"),
            },
        }

        if dry_run:
            return {"ok": True, "data": {
                **datos,
                "sales_intent": sales_intent,
                "sales_context": sales_context,
                "dry_run": True,
                "comment_id": context.get("comment_id"),
                "commenter_ig_id": commenter_ig_id,
                "sales_result": None,
            }}

        sales_result = None
        if datos.get("es_lead") and commenter_ig_id:
            sales_context["dry_run"] = False
            sales_result = _run("vertical_sales/sales_run", sales_context)

        return {"ok": True, "data": {
            **datos,
            "dry_run": False,
            "comment_id": context.get("comment_id"),
            "commenter_ig_id": commenter_ig_id,
            "sales_intent": sales_intent,
            "sales_result": sales_result,
        }}

    def _clasificar(self, comment_text: str, post_context: str) -> dict:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return {"ok": False, "error": "ANTHROPIC_API_KEY no configurada"}

        payload = {
            "model": _MODEL,
            "max_tokens": 512,
            "messages": [{"role": "user", "content": _PROMPT.format(
                comment_text=comment_text,
                post_context=post_context,
            )}],
        }
        try:
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=json.dumps(payload).encode(),
                headers={
                    "content-type":      "application/json",
                    "x-api-key":         api_key,
                    "anthropic-version": "2023-06-01",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as r:
                resp = json.loads(r.read().decode())
            raw = resp["content"][0]["text"].strip()
            data = self._parse_json(raw)
            return {"ok": True, "data": data}
        except Exception as e:
            return {"ok": False, "error": f"Haiku error: {e}"}

    def _parse_json(self, raw: str) -> dict:
        text = raw.strip()
        if text.startswith("```"):
            text = text.strip("`").strip()
            if text.lower().startswith("json"):
                text = text[4:].strip()
        try:
            data = json.loads(text)
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                data = json.loads(text[start:end + 1])
                return data if isinstance(data, dict) else {}
            raise
