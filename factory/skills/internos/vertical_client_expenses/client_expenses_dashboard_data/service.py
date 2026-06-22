from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path


_FACTORY_DIR = Path(__file__).resolve().parents[4]
_CLIENT_PROJECTS_PATH = _FACTORY_DIR / "config" / "client_projects.json"


class ClientExpensesDashboardDataService:
    def ejecutar(self, context: dict) -> dict:
        auth = self._authorize(context)
        if not auth["ok"]:
            return auth

        schema = self._schema(context)
        if not schema:
            return {"ok": False, "error": "schema requerido o client_id/project_code conocidos"}

        action = (context.get("action") or "stats").strip().lower()
        try:
            if action == "list":
                return self._list(schema, context)
            if action == "stats":
                return self._stats(schema, context)
            return {"ok": False, "error": "action invalida. Usa stats o list"}
        except Exception as exc:
            return {"ok": False, "error": f"client_expenses_dashboard_data fallo: {exc}"}

    def _authorize(self, context: dict) -> dict:
        expected = os.getenv("CLIENT_EXPENSES_DASHBOARD_KEY") or os.getenv("DURALON_DASHBOARD_KEY")
        if not expected:
            return {"ok": True}
        received = context.get("dashboard_key") or context.get("key") or ""
        if received != expected:
            return {"ok": False, "error": "dashboard_key invalido"}
        return {"ok": True}

    def _schema(self, context: dict) -> str:
        explicit = context.get("schema") or context.get("supabase_schema")
        if explicit:
            schema = str(explicit)
            return schema if schema in self._allowed_schemas() else ""
        project = self._project_config(context)
        return str(project.get("schema") or "")

    def _allowed_schemas(self) -> set[str]:
        raw = os.getenv("CLIENT_EXPENSES_ALLOWED_SCHEMAS", "")
        configured = {item.strip() for item in raw.split(",") if item.strip()}
        config_schemas = {
            str(project.get("schema"))
            for projects in self._client_projects().values()
            for project in projects.values()
            if isinstance(project, dict) and project.get("schema")
        }
        return config_schemas | configured

    def _project_config(self, context: dict) -> dict:
        # Acepta company_id actual o client_id legacy.
        company_id = (
            str(context.get("company_id") or context.get("empresa_id") or "").strip()
            or str(context.get("client_id") or "").strip()
        )
        project_code = str(context.get("project_code") or "").strip()
        all_projects = self._client_projects()
        projects = all_projects.get(company_id, {})
        # Si es un alias, seguir al original
        project = projects.get(project_code, {}) if isinstance(projects, dict) else {}
        if isinstance(project, dict) and project.get("alias_of"):
            projects = all_projects.get(project["alias_of"], {})
            project = projects.get(project_code, {}) if isinstance(projects, dict) else {}
        return project if isinstance(project, dict) else {}

    def _client_projects(self) -> dict:
        if not _CLIENT_PROJECTS_PATH.exists():
            return {}
        try:
            data = json.loads(_CLIENT_PROJECTS_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
        return data if isinstance(data, dict) else {}

    def _headers(self, schema: str) -> dict:
        service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        if not service_key:
            raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY no configurada")
        return {
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Accept": "application/json",
            "Accept-Profile": schema,
        }

    def _get(self, schema: str, path: str) -> list[dict]:
        base_url = os.getenv("SUPABASE_URL", "").rstrip("/")
        if not base_url:
            raise RuntimeError("SUPABASE_URL no configurada")
        req = urllib.request.Request(f"{base_url}/rest/v1/{path}", headers=self._headers(schema))
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

    def _list(self, schema: str, context: dict) -> dict:
        limit = max(1, min(int(context.get("limit", 200)), 2000))
        select_with_bank = "folio,fecha,monto,descripcion,metodo_captura,vehiculo,cta_retiro_id,cta_retiro_folio,cta_retiro_nombre,categorias_gasto(nombre),usuarios(nombre)"
        select_basic = "folio,fecha,monto,descripcion,metodo_captura,vehiculo,categorias_gasto(nombre),usuarios(nombre)"
        params = [
            f"select={select_with_bank}",
            "order=fecha.desc",
            f"limit={limit}",
        ]
        if context.get("fecha_desde"):
            params.append(f"fecha=gte.{urllib.parse.quote(str(context['fecha_desde']))}")
        if context.get("fecha_hasta"):
            params.append(f"fecha=lte.{urllib.parse.quote(str(context['fecha_hasta']))}")

        try:
            rows = self._get(schema, "gastos?" + "&".join(params))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace").lower()
            if "cta_retiro" not in body and "schema cache" not in body and "pgrst204" not in body:
                raise
            rows = self._get(schema, "gastos?" + "&".join([f"select={select_basic}", *params[1:]]))
        gastos = [self._format_gasto(row) for row in rows]
        return {"ok": True, "data": {"gastos": gastos, "total": len(gastos), "schema": schema}}

    def _stats(self, schema: str, context: dict) -> dict:
        result = self._list(schema, {**context, "limit": context.get("stats_limit", 2000)})
        if not result.get("ok"):
            return result
        gastos = result["data"]["gastos"]
        if not gastos:
            return {"ok": True, "data": {
                "total": 0,
                "count": 0,
                "avg": 0,
                "por_categoria": [],
                "totalMes": 0,
                "totalMesAnt": 0,
                "variacion": 0,
                "schema": schema,
            }}

        total = sum(g["monto"] for g in gastos)
        count = len(gastos)
        avg = total / count

        by_category: dict[str, dict[str, float | int]] = {}
        for gasto in gastos:
            category = gasto["categoria"] or "Sin categoria"
            if category not in by_category:
                by_category[category] = {"total": 0.0, "count": 0}
            by_category[category]["total"] = float(by_category[category]["total"]) + gasto["monto"]
            by_category[category]["count"] = int(by_category[category]["count"]) + 1

        por_categoria = sorted(
            [{"categoria": name, "total": round(float(values["total"]), 2), "count": int(values["count"])} for name, values in by_category.items()],
            key=lambda row: -row["total"],
        )

        today = date.today()
        current_month = today.strftime("%Y-%m")
        previous_month = date(today.year if today.month > 1 else today.year - 1, today.month - 1 if today.month > 1 else 12, 1).strftime("%Y-%m")
        total_mes = sum(g["monto"] for g in gastos if g["fecha"].startswith(current_month))
        total_mes_ant = sum(g["monto"] for g in gastos if g["fecha"].startswith(previous_month))
        variacion = ((total_mes - total_mes_ant) / total_mes_ant * 100) if total_mes_ant > 0 else 0

        return {"ok": True, "data": {
            "total": round(total, 2),
            "count": count,
            "avg": round(avg, 2),
            "por_categoria": por_categoria,
            "totalMes": round(total_mes, 2),
            "totalMesAnt": round(total_mes_ant, 2),
            "variacion": round(variacion, 2),
            "schema": schema,
        }}

    def _format_gasto(self, row: dict) -> dict:
        return {
            "folio": row.get("folio", ""),
            "fecha": row.get("fecha", ""),
            "monto": float(row.get("monto") or 0),
            "descripcion": row.get("descripcion") or "",
            "metodo_captura": row.get("metodo_captura") or "manual",
            "vehiculo": row.get("vehiculo") or None,
            "cta_retiro_id": row.get("cta_retiro_id"),
            "cta_retiro_folio": row.get("cta_retiro_folio"),
            "cta_retiro_nombre": row.get("cta_retiro_nombre"),
            "categoria": (row.get("categorias_gasto") or {}).get("nombre") or "",
            "nombre_usuario": (row.get("usuarios") or {}).get("nombre") or "",
        }
