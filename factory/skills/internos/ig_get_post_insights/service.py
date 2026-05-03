"""Service for ig_get_post_insights - fetches engagement metrics for an Instagram post."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

_VALID_METRICS = {
    "views", "reach", "likes", "comments", "shares", "saved",
    "video_views", "ig_reels_avg_watch_time",
    "ig_reels_video_view_total_time", "total_interactions",
}
_DEFAULT_METRICS = ["views", "reach", "likes", "comments", "shares", "saved"]


class IgGetPostInsightsService:

    def ejecutar(self, context: dict) -> dict:
        valido, error = self._validar(context)
        if not valido:
            return {"ok": False, "error": error}
        if context.get("dry_run", False):
            return {"ok": True, "message": "dry_run", "data": context}
        return self._ejecutar(context)

    def _validar(self, context: dict) -> tuple[bool, str | None]:
        if not context.get("media_id") or not isinstance(context["media_id"], str):
            return False, "media_id es requerido y debe ser texto"
        metrics = context.get("metrics")
        if metrics is not None:
            if not isinstance(metrics, list) or not metrics:
                return False, "metrics debe ser una lista no vacia"
            invalid = [m for m in metrics if m not in _VALID_METRICS]
            if invalid:
                return False, f"metricas invalidas: {invalid}. Validas: {sorted(_VALID_METRICS)}"
        return True, None

    def _ejecutar(self, context: dict) -> dict:
        media_id = context["media_id"]
        metrics = context.get("metrics", _DEFAULT_METRICS)

        access_token = self._access_token(context)
        if not access_token:
            return {"ok": False, "error": "IG_ACCESS_TOKEN no configurada"}

        metric_str = ",".join(metrics)
        params = {"metric": metric_str, "access_token": access_token}
        graph_version = os.getenv("IG_GRAPH_API_VERSION", "v24.0")
        url = f"https://graph.facebook.com/{graph_version}/{media_id}/insights?" + urllib.parse.urlencode(params)

        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=45) as response:
                result = json.loads(response.read().decode("utf-8"))

            parsed: dict = {}
            for item in result.get("data", []):
                name = item.get("name", "")
                try:
                    values = item.get("values", [])
                    parsed[name] = values[0]["value"] if values else item.get("value", 0)
                except (KeyError, IndexError):
                    parsed[name] = 0

            return {"ok": True, "data": {"media_id": media_id, "metrics": parsed}}
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

    def _access_token(self, context: dict) -> str | None:
        return context.get("access_token") or self._connection(context).get("access_token") or os.getenv("IG_ACCESS_TOKEN") or os.getenv("META_ACCESS_TOKEN")
