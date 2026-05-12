from __future__ import annotations
import json, os, urllib.request
from pathlib import Path

_MODEL = "claude-haiku-4-5-20251001"
_PROMPT = """Eres un asistente de ventas de Instagram. Genera una respuesta {tono} y natural al siguiente mensaje.

Contexto del negocio: {contexto_negocio}
Mensaje recibido: {texto}

Responde SOLO con JSON válido:
{{
  "respuesta": "texto de la respuesta (máx 300 chars para comentario, 1000 para DM)",
  "incluir_cta": true/false,
  "tono_usado": "amigable|profesional|urgente"
}}"""


def _runner():
    from factory.engine import SkillLoader, SkillRunner
    root = Path(__file__).parent.parent.parent
    ext_root = root.parent / "externos"
    ext_root.mkdir(parents=True, exist_ok=True)
    loader = SkillLoader(internal_root=root, external_root=ext_root,
                         extra_roots={"meta": root.parent / "meta", "eval": root.parent / "eval"})
    return SkillRunner(loader)


def _run(name: str, ctx: dict) -> dict:
    return _runner().run(name, ctx, source="internos")


class IgAutoResponderService:

    def ejecutar(self, context: dict) -> dict:
        trigger_type = (context.get("trigger_type") or "dm").strip().lower()
        texto = (context.get("texto") or context.get("message_text") or "").strip()
        sender_ig_id = (context.get("sender_ig_id") or context.get("ig_user_id") or "").strip()
        comment_id = (context.get("comment_id") or "").strip()
        contexto_negocio = (context.get("contexto_negocio") or "venta de propiedades inmobiliarias").strip()
        tono = (context.get("tono") or "amigable").strip()
        dry_run = context.get("dry_run", True)

        if not texto:
            return {"ok": False, "error": "texto requerido"}
        if trigger_type == "dm" and not sender_ig_id:
            return {"ok": False, "error": "sender_ig_id requerido para trigger_type=dm"}
        if trigger_type == "comment" and not comment_id:
            return {"ok": False, "error": "comment_id requerido para trigger_type=comment"}

        gen = self._generar_respuesta(texto, contexto_negocio, tono)
        if not gen.get("ok"):
            return gen

        respuesta = gen["data"]["respuesta"]

        if dry_run:
            return {"ok": True, "data": {
                "dry_run": True,
                "trigger_type": trigger_type,
                "respuesta_generada": respuesta,
                "enviado": False,
            }}

        access_token = context.get("access_token") or os.getenv("IG_ACCESS_TOKEN") or os.getenv("META_ACCESS_TOKEN")

        if trigger_type == "dm":
            result = _run("vertical_instagram/ig_reply_dm", {
                "recipient_ig_id": sender_ig_id,
                "message":         respuesta,
                "access_token":    access_token,
                "dry_run":         False,
            })
        else:
            result = _run("vertical_instagram/ig_reply_comment", {
                "comment_id":   comment_id,
                "message":      respuesta[:2200],
                "access_token": access_token,
                "dry_run":      False,
            })

        return {"ok": True, "data": {
            "trigger_type":       trigger_type,
            "respuesta_generada": respuesta,
            "enviado":            result.get("ok", False),
            "send_result":        result.get("data"),
            "send_error":         result.get("error") if not result.get("ok") else None,
        }}

    def _generar_respuesta(self, texto: str, contexto_negocio: str, tono: str) -> dict:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return {"ok": False, "error": "ANTHROPIC_API_KEY no configurada"}
        payload = {
            "model": _MODEL,
            "max_tokens": 512,
            "messages": [{"role": "user", "content": _PROMPT.format(
                texto=texto, contexto_negocio=contexto_negocio, tono=tono,
            )}],
        }
        try:
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=json.dumps(payload).encode(),
                headers={"content-type": "application/json", "x-api-key": api_key,
                         "anthropic-version": "2023-06-01"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as r:
                resp = json.loads(r.read().decode())
            data = json.loads(resp["content"][0]["text"].strip())
            return {"ok": True, "data": data}
        except Exception as e:
            return {"ok": False, "error": f"Haiku error: {e}"}
