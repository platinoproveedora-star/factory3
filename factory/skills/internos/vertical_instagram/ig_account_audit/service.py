from __future__ import annotations
import json, os, urllib.request, urllib.parse, urllib.error

_VERSION = "v24.0"
_UA = "FactoryFactory/0.1 (+https://github.com/)"
_MODEL = "claude-haiku-4-5-20251001"
_PROMPT = """Audita esta cuenta de Instagram y da recomendaciones concretas para mejorar captación de leads.

Perfil: {perfil}
Insights (si disponibles): {insights}
Últimos posts: {posts}

Responde SOLO con JSON válido:
{{
  "score_general": 1-10,
  "puntos_fuertes": ["fortaleza 1", "fortaleza 2"],
  "areas_mejora": ["área 1", "área 2"],
  "recomendaciones": [
    {{"prioridad": "alta|media|baja", "accion": "descripción concreta"}},
    ...
  ],
  "bio_optimizada": "versión mejorada de la bio si aplica",
  "frecuencia_ideal": "X posts/semana",
  "mejor_horario": "franja horaria sugerida"
}}"""


class IgAccountAuditService:

    def ejecutar(self, context: dict) -> dict:
        ig_user_id = (context.get("ig_user_id") or os.getenv("IG_USER_ID") or "").strip()
        access_token = (context.get("access_token") or os.getenv("IG_ACCESS_TOKEN") or os.getenv("META_ACCESS_TOKEN") or "").strip()
        limit_posts = min(int(context.get("limit_posts") or 15), 25)

        if not ig_user_id:
            return {"ok": False, "error": "ig_user_id requerido (o IG_USER_ID en env)"}
        if not access_token:
            return {"ok": False, "error": "access_token requerido"}

        perfil = self._get_perfil(ig_user_id, access_token)
        if not perfil.get("ok"):
            return perfil

        posts = self._get_posts(ig_user_id, access_token, limit_posts)
        posts_data = posts.get("data", []) if posts.get("ok") else []

        insights = self._get_insights(ig_user_id, access_token)
        insights_data = insights.get("data", {}) if insights.get("ok") else {}

        posts_resumen = [
            {
                "tipo":        p.get("media_type"),
                "likes":       p.get("like_count", 0),
                "comentarios": p.get("comments_count", 0),
                "caption":     (p.get("caption") or "")[:200],
                "fecha":       p.get("timestamp", "")[:10],
            }
            for p in posts_data
        ]

        auditoria = self._auditar(perfil["data"], insights_data, posts_resumen)

        return {"ok": True, "data": {
            "ig_user_id":   ig_user_id,
            "perfil":       perfil["data"],
            "posts_analizados": len(posts_resumen),
            "auditoria":    auditoria.get("data") if auditoria.get("ok") else None,
            "auditoria_error": auditoria.get("error") if not auditoria.get("ok") else None,
        }}

    def _get_perfil(self, ig_id: str, token: str) -> dict:
        params = {
            "fields": "name,biography,followers_count,follows_count,media_count,username,website",
            "access_token": token,
        }
        qs = urllib.parse.urlencode(params)
        url = f"https://graph.facebook.com/{_VERSION}/{ig_id}?{qs}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": _UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read().decode())
            if "error" in data:
                return {"ok": False, "error": data["error"].get("message", str(data["error"]))}
            return {"ok": True, "data": data}
        except urllib.error.HTTPError as exc:
            try:
                err = json.loads(exc.read().decode())
                msg = err.get("error", {}).get("message", str(exc))
            except Exception:
                msg = str(exc)
            return {"ok": False, "error": msg}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _get_posts(self, ig_id: str, token: str, limit: int) -> dict:
        params = {
            "fields": "id,caption,timestamp,like_count,comments_count,media_type",
            "limit":  limit,
            "access_token": token,
        }
        qs = urllib.parse.urlencode(params)
        url = f"https://graph.facebook.com/{_VERSION}/{ig_id}/media?{qs}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": _UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read().decode())
            return {"ok": True, "data": data.get("data", [])}
        except Exception:
            return {"ok": True, "data": []}

    def _get_insights(self, ig_id: str, token: str) -> dict:
        params = {
            "metric": "follower_count,reach,impressions",
            "period": "day",
            "access_token": token,
        }
        qs = urllib.parse.urlencode(params)
        url = f"https://graph.facebook.com/{_VERSION}/{ig_id}/insights?{qs}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": _UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read().decode())
            return {"ok": True, "data": data.get("data", {})}
        except Exception:
            return {"ok": True, "data": {}}

    def _auditar(self, perfil: dict, insights: dict, posts: list) -> dict:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return {"ok": False, "error": "ANTHROPIC_API_KEY no configurada"}
        payload = {
            "model": _MODEL,
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": _PROMPT.format(
                perfil=json.dumps(perfil, ensure_ascii=False),
                insights=json.dumps(insights, ensure_ascii=False),
                posts=json.dumps(posts[:10], ensure_ascii=False),
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
