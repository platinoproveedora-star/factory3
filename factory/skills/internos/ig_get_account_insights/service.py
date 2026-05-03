"""Service for ig_get_account_insights - fetches account-level metrics from Instagram Graph API."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

_VALID_METRICS = {"views", "reach", "impressions", "follower_count", "profile_views", "website_clicks", "accounts_engaged"}
_VALID_PERIODS = {"day", "week", "month"}
_DEFAULT_METRICS = ["views", "reach", "follower_count"]


class IgGetAccountInsightsService:

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
        metrics = context.get("metrics")
        if metrics is not None:
            if not isinstance(metrics, list) or not metrics:
                return False, "metrics debe ser una lista no vacia"
            invalid = [m for m in metrics if m not in _VALID_METRICS]
            if invalid:
                return False, f"metricas invalidas: {invalid}. Validas: {sorted(_VALID_METRICS)}"
        period = context.get("period")
        if period is not None and period not in _VALID_PERIODS:
            return False, f"period debe ser uno de: {', '.join(sorted(_VALID_PERIODS))}"
        return True, None

    def _ejecutar(self, context: dict) -> dict:
        ig_user_id = self._ig_user_id(context)
        metrics = context.get("metrics", _DEFAULT_METRICS)
        period = context.get("period", "day")
        since = context.get("since")
        until = context.get("until")

        access_token = self._access_token(context)
        if not access_token:
            return {"ok": False, "error": "IG_ACCESS_TOKEN no configurada"}

        params: dict = {"metric": ",".join(metrics), "period": period, "access_token": access_token}
        if since:
            params["since"] = since
        if until:
            params["until"] = until
        graph_version = os.getenv("IG_GRAPH_API_VERSION", "v24.0")
        url = f"https://graph.facebook.com/{graph_version}/{ig_user_id}/insights?" + urllib.parse.urlencode(params)

        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=45) as response:
                result = json.loads(response.read().decode("utf-8"))

            parsed: dict = {}
            for item in result.get("data", []):
                name = item.get("name", "")
                values = item.get("values", [])
                if len(values) == 1:
                    parsed[name] = values[0].get("value", 0)
                else:
                    parsed[name] = [{"value": v.get("value", 0), "end_time": v.get("end_time")} for v in values]

            return {"ok": True, "data": {"ig_user_id": ig_user_id, "period": period, "metrics": parsed}}
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
