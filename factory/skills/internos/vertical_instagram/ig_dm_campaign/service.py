from __future__ import annotations
import json, os, time, urllib.request
from pathlib import Path

_MODEL = "claude-haiku-4-5-20251001"
_PROMPT_IA = """Escribe un DM de Instagram personalizado para este usuario.

Contexto del negocio: {contexto_negocio}
Info del usuario: {info_usuario}
Objetivo del mensaje: {objetivo}

Responde SOLO con JSON válido:
{{
  "mensaje": "texto del DM (máx 1000 chars, natural, sin spam)",
  "personalizado": true/false
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


class IgDmCampaignService:

    def ejecutar(self, context: dict) -> dict:
        ig_user_ids = context.get("ig_user_ids") or []
        mensaje_estatico = (context.get("mensaje") or "").strip()
        usar_ia = context.get("usar_ia", False)
        contexto_negocio = (context.get("contexto_negocio") or "").strip()
        objetivo = (context.get("objetivo") or "presentar nuestra oferta").strip()
        delay_seg = float(context.get("delay_seg") or 1.0)
        dry_run = context.get("dry_run", True)
        access_token = context.get("access_token") or os.getenv("IG_ACCESS_TOKEN") or os.getenv("META_ACCESS_TOKEN") or ""

        if not ig_user_ids:
            return {"ok": False, "error": "ig_user_ids requerido (lista de IDs)"}
        if not mensaje_estatico and not usar_ia:
            return {"ok": False, "error": "mensaje requerido, o usar_ia=True con contexto_negocio"}
        if usar_ia and not contexto_negocio:
            return {"ok": False, "error": "contexto_negocio requerido cuando usar_ia=True"}
        if not access_token and not dry_run:
            return {"ok": False, "error": "access_token requerido (o IG_ACCESS_TOKEN en env)"}

        enviados, errores, detalle = 0, 0, []

        for uid in ig_user_ids:
            uid = str(uid).strip()
            if not uid:
                continue

            if usar_ia:
                gen = self._generar_mensaje(uid, contexto_negocio, objetivo)
                if not gen.get("ok"):
                    errores += 1
                    detalle.append({"ig_user_id": uid, "error": gen.get("error")})
                    continue
                mensaje = gen["data"]["mensaje"]
            else:
                mensaje = mensaje_estatico

            if dry_run:
                detalle.append({"ig_user_id": uid, "mensaje": mensaje[:80] + "...", "dry_run": True})
                enviados += 1
                continue

            result = _run("vertical_instagram/ig_reply_dm", {
                "recipient_ig_id": uid,
                "message":         mensaje,
                "access_token":    access_token,
                "dry_run":         False,
            })

            if result.get("ok"):
                enviados += 1
                detalle.append({"ig_user_id": uid, "enviado": True, "message_id": result.get("data", {}).get("message_id")})
            else:
                errores += 1
                detalle.append({"ig_user_id": uid, "enviado": False, "error": result.get("error")})

            if delay_seg > 0 and not dry_run:
                time.sleep(delay_seg)

        return {"ok": True, "data": {
            "total":    len(ig_user_ids),
            "enviados": enviados,
            "errores":  errores,
            "dry_run":  dry_run,
            "detalle":  detalle,
        }}

    def _generar_mensaje(self, uid: str, contexto_negocio: str, objetivo: str) -> dict:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return {"ok": False, "error": "ANTHROPIC_API_KEY no configurada"}
        payload = {
            "model": _MODEL,
            "max_tokens": 512,
            "messages": [{"role": "user", "content": _PROMPT_IA.format(
                contexto_negocio=contexto_negocio,
                info_usuario=f"ig_user_id={uid}",
                objetivo=objetivo,
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
