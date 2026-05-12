from __future__ import annotations
import json, os, time, urllib.request, urllib.parse, urllib.error
from pathlib import Path

_VERSION = "v24.0"
_UA = "FactoryFactory/0.1 (+https://github.com/)"


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


class IgCommentMonitorService:

    def ejecutar(self, context: dict) -> dict:
        # media_id único o lista
        media_id = (context.get("media_id") or "").strip()
        media_ids = context.get("media_ids") or []
        if media_id:
            media_ids = [media_id] + [m for m in media_ids if m != media_id]
        if not media_ids:
            return {"ok": False, "error": "media_id o media_ids requerido"}

        access_token = (context.get("access_token") or os.getenv("IG_ACCESS_TOKEN") or os.getenv("META_ACCESS_TOKEN") or "").strip()
        empresa_id = (context.get("empresa_id") or "").strip()
        post_context = (context.get("post_context") or "publicación de Instagram").strip()
        auto_reply = context.get("auto_reply", False)
        dry_run = context.get("dry_run", True)

        # since: unix timestamp. Default: últimas 24h
        since = context.get("since") or int(time.time()) - 86400

        if not access_token:
            return {"ok": False, "error": "access_token requerido (o IG_ACCESS_TOKEN en env)"}
        if not empresa_id:
            return {"ok": False, "error": "empresa_id requerido"}

        total_comentarios = 0
        leads_detectados = 0
        respuestas_enviadas = 0
        detalle = []

        for mid in media_ids:
            result = self._procesar_post(
                mid, access_token, empresa_id, post_context,
                since, auto_reply, dry_run,
            )
            if not result.get("ok"):
                detalle.append({"media_id": mid, "error": result.get("error")})
                continue
            d = result["data"]
            total_comentarios += d.get("comentarios", 0)
            leads_detectados += d.get("leads", 0)
            respuestas_enviadas += d.get("respuestas", 0)
            detalle.append({"media_id": mid, **d})

        return {"ok": True, "data": {
            "total_comentarios": total_comentarios,
            "leads_detectados":  leads_detectados,
            "respuestas_enviadas": respuestas_enviadas,
            "dry_run": dry_run,
            "detalle": detalle,
        }}

    def _procesar_post(self, media_id, token, empresa_id, post_context, since, auto_reply, dry_run):
        comments_result = self._fetch_comments(media_id, token, since)
        if not comments_result.get("ok"):
            return comments_result

        comments = comments_result["data"]
        leads, respuestas, items = 0, 0, []

        for c in comments:
            comment_id = c.get("id", "")
            texto = c.get("text", "").strip()
            commenter_id = c.get("from", {}).get("id", "")
            username = c.get("from", {}).get("username", "")

            if not texto:
                continue

            detect = _run("vertical_instagram/ig_comment_lead_detect", {
                "comment_id":      comment_id,
                "comment_text":    texto,
                "commenter_ig_id": commenter_id,
                "post_id":         media_id,
                "empresa_id":      empresa_id,
                "post_context":    post_context,
                "dry_run":         dry_run,
            })

            es_lead = detect.get("data", {}).get("es_lead", False) if detect.get("ok") else False
            accion = detect.get("data", {}).get("accion_sugerida", "ignorar") if detect.get("ok") else "ignorar"
            respuesta_sugerida = detect.get("data", {}).get("respuesta_sugerida", "") if detect.get("ok") else ""

            if es_lead:
                leads += 1

            reply_result = None
            if es_lead and auto_reply and accion == "responder_publico" and respuesta_sugerida and not dry_run:
                reply_result = _run("vertical_instagram/ig_reply_comment", {
                    "comment_id": comment_id,
                    "message":    respuesta_sugerida,
                    "access_token": token,
                    "dry_run":    False,
                })
                if reply_result.get("ok"):
                    respuestas += 1

            items.append({
                "comment_id":  comment_id,
                "username":    username,
                "texto":       texto[:120],
                "es_lead":     es_lead,
                "accion":      accion,
                "reply_sent":  reply_result.get("ok", False) if reply_result else False,
            })

        return {"ok": True, "data": {
            "comentarios": len(comments),
            "leads":       leads,
            "respuestas":  respuestas,
            "items":       items,
        }}

    def _fetch_comments(self, media_id: str, token: str, since: int) -> dict:
        params = {
            "fields": "id,text,timestamp,from",
            "since":  since,
            "limit":  100,
            "access_token": token,
        }
        qs = urllib.parse.urlencode(params)
        url = f"https://graph.facebook.com/{_VERSION}/{media_id}/comments?{qs}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": _UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read().decode())
            if "error" in data:
                return {"ok": False, "error": data["error"].get("message", str(data["error"]))}
            return {"ok": True, "data": data.get("data", [])}
        except urllib.error.HTTPError as exc:
            try:
                err = json.loads(exc.read().decode())
                msg = err.get("error", {}).get("message", str(exc))
            except Exception:
                msg = str(exc)
            return {"ok": False, "error": msg}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
