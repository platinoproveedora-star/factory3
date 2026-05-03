"""Service for ig_top_posts_analyzer - ranks an account's posts by a given engagement metric."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

_VALID_METRICS = {"views", "reach", "likes", "comments", "shares", "saved"}


class IgTopPostsAnalyzerService:

    def ejecutar(self, context: dict) -> dict:
        valido, error = self._validar(context)
        if not valido:
            return {"ok": False, "error": error}
        if context.get("dry_run", False):
            return {"ok": True, "message": "dry_run", "data": context}
        return self._ejecutar(context)

    def _validar(self, context: dict) -> tuple[bool, str | None]:
        ig_user_id = self._ig_user_id(context)
        if not ig_user_id or not isinstance(ig_user_id, str):
            return False, "ig_user_id es requerido en context o IG_BUSINESS_ACCOUNT_ID en variables de entorno"
        limit = context.get("limit")
        if limit is not None and (not isinstance(limit, int) or limit < 5 or limit > 50):
            return False, "limit debe ser un entero entre 5 y 50"
        metric = context.get("metric")
        if metric is not None and metric not in _VALID_METRICS:
            return False, f"metric debe ser uno de: {', '.join(sorted(_VALID_METRICS))}"
        return True, None

    def _ejecutar(self, context: dict) -> dict:
        ig_user_id = self._ig_user_id(context)
        limit = context.get("limit", 10)
        metric = context.get("metric", "views")

        access_token = self._access_token(context)
        if not access_token:
            return {"ok": False, "error": "IG_ACCESS_TOKEN no configurada"}

        try:
            fetch_count = min(limit * 2, 100)
            params = {"fields": "id,permalink,timestamp,media_type", "limit": fetch_count, "access_token": access_token}
            graph_version = os.getenv("IG_GRAPH_API_VERSION", "v24.0")
            url = f"https://graph.facebook.com/{graph_version}/{ig_user_id}/media?" + urllib.parse.urlencode(params)
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=45) as response:
                media_result = json.loads(response.read().decode("utf-8"))
            media_list = media_result.get("data", [])

            ranked = []
            for post in media_list:
                media_id = post["id"]
                try:
                    ins_params = {"metric": metric, "access_token": access_token}
                    ins_url = f"https://graph.facebook.com/{graph_version}/{media_id}/insights?" + urllib.parse.urlencode(ins_params)
                    ins_req = urllib.request.Request(ins_url, method="GET")
                    with urllib.request.urlopen(ins_req, timeout=30) as ins_resp:
                        ins_result = json.loads(ins_resp.read().decode("utf-8"))
                    ins_data = ins_result.get("data", [])
                    values = ins_data[0].get("values", []) if ins_data else []
                    metric_value = values[0]["value"] if values else ins_data[0].get("value", 0) if ins_data else 0
                except Exception:
                    metric_value = 0
                ranked.append({"media_id": media_id, "permalink": post.get("permalink", ""), "timestamp": post.get("timestamp", ""), "media_type": post.get("media_type", ""), "metric_value": metric_value})

            ranked.sort(key=lambda x: x["metric_value"], reverse=True)
            top = ranked[:limit]
            for i, post in enumerate(top):
                post["rank"] = i + 1

            return {"ok": True, "data": {"ig_user_id": ig_user_id, "metric": metric, "total_analyzed": len(ranked), "top_posts": top}}
        except urllib.error.HTTPError as exc:
            try:
                body = json.loads(exc.read().decode("utf-8"))
                msg = body.get("error", {}).get("message", str(exc))
            except Exception:
                msg = str(exc)
            return {"ok": False, "error": msg}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _connection(self, context: dict) -> dict:
        connection = context.get("connection")
        return connection if isinstance(connection, dict) else {}

    def _ig_user_id(self, context: dict) -> str | None:
        return context.get("ig_user_id") or self._connection(context).get("ig_user_id") or os.getenv("IG_BUSINESS_ACCOUNT_ID")

    def _access_token(self, context: dict) -> str | None:
        return context.get("access_token") or self._connection(context).get("access_token") or os.getenv("IG_ACCESS_TOKEN") or os.getenv("META_ACCESS_TOKEN")
