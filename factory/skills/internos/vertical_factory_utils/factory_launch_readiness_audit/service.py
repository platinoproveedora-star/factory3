"""Audita infraestructura y huecos operativos antes de comercializar.

Combina: (1) chequeos en vivo de plan/tier en Vercel, Render y Supabase,
(2) presencia de variables de billing/monitoreo/email, y (3) un checklist
curado de trabajo pendiente con horas estimadas, marcando cuales ya se
resolvieron segun lo que se detecto en vivo.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request


_ENV_GROUPS = {
    "billing": ["STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET", "STRIPE_PUBLISHABLE_KEY"],
    "monitoring": ["SENTRY_DSN"],
    "email": ["RESEND_API_KEY", "SENDGRID_API_KEY"],
}

# Checklist curado: horas son estimaciones, no medicion real.
_WORK_ITEMS = [
    {"id": "vercel_pro", "categoria": "infra", "item": "Subir proyectos de Vercel a plan Pro (Hobby prohibe uso comercial)", "prioridad": "blocker", "horas": 2, "check": "vercel_plan"},
    {"id": "render_plan", "categoria": "infra", "item": "Confirmar/subir plan de Render (evitar cold-starts y limites de horas)", "prioridad": "blocker", "horas": 2, "check": "render_plan"},
    {"id": "supabase_plan", "categoria": "infra", "item": "Confirmar/subir plan de Supabase (backups, pooling, limites de fila)", "prioridad": "blocker", "horas": 2, "check": "supabase_plan"},
    {"id": "sso_token_hardening", "categoria": "seguridad", "item": "Cambiar SSO de JWT completo en URL a codigo de un solo uso de corta duracion", "prioridad": "high", "horas": 4, "check": None},
    {"id": "rls_defense", "categoria": "seguridad", "item": "Agregar RLS como segunda capa (hoy todo pasa por service role, sin aislamiento a nivel DB)", "prioridad": "medium", "horas": 16, "check": None},
    {"id": "rate_limiting", "categoria": "seguridad", "item": "Rate limiting en rutas publicas de login/API (mas alla del throttle de login actual)", "prioridad": "high", "horas": 6, "check": None},
    {"id": "secrets_rotation", "categoria": "seguridad", "item": "Practica de rotacion de secrets (hoy todos en un .env de una sola maquina)", "prioridad": "medium", "horas": 4, "check": None},
    {"id": "error_monitoring", "categoria": "operacion", "item": "Monitoreo de errores con alertas (Sentry o equivalente)", "prioridad": "high", "horas": 4, "check": "monitoring_env"},
    {"id": "structured_logging", "categoria": "operacion", "item": "Logging estructurado + dashboard basico de salud", "prioridad": "medium", "horas": 6, "check": None},
    {"id": "backup_verification", "categoria": "operacion", "item": "Verificar backups/point-in-time recovery en Supabase + runbook de recuperacion", "prioridad": "high", "horas": 3, "check": None},
    {"id": "load_testing", "categoria": "operacion", "item": "Prueba de carga contra dashboards y endpoints de skills", "prioridad": "high", "horas": 10, "check": None},
    {"id": "cost_alerting", "categoria": "operacion", "item": "Alertas de gasto (Anthropic, Meta Ads, Vercel/Render/Supabase) para evitar sorpresas de facturacion", "prioridad": "medium", "horas": 3, "check": None},
    {"id": "email_transaccional", "categoria": "producto", "item": "Correos transaccionales (verificacion, bienvenida, recuperacion de password)", "prioridad": "high", "horas": 6, "check": "email_env"},
    {"id": "legal_paginas", "categoria": "legal", "item": "Terminos de servicio, aviso de privacidad (LFPDPPP) y manejo de datos fiscales sensibles", "prioridad": "blocker", "horas": 8, "check": None},
    {"id": "soporte_proceso", "categoria": "operacion", "item": "Proceso de soporte/ticketing y SLA basico", "prioridad": "medium", "horas": 6, "check": None},
    {"id": "stripe_billing", "categoria": "producto", "item": "Integracion Stripe: checkout, webhooks, activacion/baja de grants por suscripcion", "prioridad": "blocker", "horas": 20, "check": "billing_env", "ya_conocido": True},
    {"id": "module_assignment", "categoria": "producto", "item": "Flujo de asignacion de modulos/onboarding self-serve por empresa", "prioridad": "blocker", "horas": 12, "check": None, "ya_conocido": True},
]


class FactoryLaunchReadinessAuditService:
    def ejecutar(self, context: dict) -> dict:
        dry_run = bool(context.get("dry_run", True))

        env_status = self._check_env_groups()
        infra_findings: list[dict] = []
        checks_run: dict[str, dict] = {}

        if dry_run:
            infra_findings.append({"check": "vercel_plan", "status": "skipped", "detail": "dry_run — sin llamadas de red"})
            infra_findings.append({"check": "render_plan", "status": "skipped", "detail": "dry_run — sin llamadas de red"})
            infra_findings.append({"check": "supabase_plan", "status": "skipped", "detail": "dry_run — sin llamadas de red"})
        else:
            vercel_result = self._check_vercel(context)
            infra_findings.append(vercel_result)
            checks_run["vercel_plan"] = vercel_result

            render_result = self._check_render(context)
            infra_findings.append(render_result)
            checks_run["render_plan"] = render_result

            supabase_result = self._check_supabase(context)
            infra_findings.append(supabase_result)
            checks_run["supabase_plan"] = supabase_result

        exclude_known = bool(context.get("exclude_known_pending", False))
        work_plan = []
        for item in _WORK_ITEMS:
            if exclude_known and item.get("ya_conocido"):
                continue
            row = dict(item)
            row["estado"] = self._resolve_status(item, env_status, checks_run, dry_run)
            work_plan.append(row)

        pending = [row for row in work_plan if row["estado"] != "resuelto"]
        total_horas = sum(row["horas"] for row in pending)
        por_prioridad: dict[str, int] = {}
        for row in pending:
            por_prioridad[row["prioridad"]] = por_prioridad.get(row["prioridad"], 0) + row["horas"]

        return {
            "ok": True,
            "message": f"{len(pending)} pendientes, {total_horas}h estimadas",
            "data": {
                "dry_run": dry_run,
                "env_status": env_status,
                "infra_findings": infra_findings,
                "work_plan": work_plan,
                "resumen": {
                    "total_items": len(work_plan),
                    "pendientes": len(pending),
                    "horas_totales_estimadas": total_horas,
                    "horas_por_prioridad": por_prioridad,
                },
            },
        }

    def _check_env_groups(self) -> dict:
        status: dict[str, dict] = {}
        for group, names in _ENV_GROUPS.items():
            present = [name for name in names if os.getenv(name)]
            status[group] = {
                "vars_esperadas": names,
                "presentes": present,
                "completo": len(present) > 0,
            }
        return status

    def _resolve_status(self, item: dict, env_status: dict, checks_run: dict, dry_run: bool) -> str:
        check = item.get("check")
        if check in ("billing_env",):
            return "resuelto" if env_status.get("billing", {}).get("completo") else "pendiente"
        if check in ("monitoring_env",):
            return "resuelto" if env_status.get("monitoring", {}).get("completo") else "pendiente"
        if check in ("email_env",):
            return "resuelto" if env_status.get("email", {}).get("completo") else "pendiente"
        if check in ("vercel_plan", "render_plan", "supabase_plan"):
            if dry_run:
                return "sin_verificar"
            result = checks_run.get(check, {})
            return "resuelto" if result.get("status") == "ok_pago" else "pendiente"
        return "pendiente_revision_manual"

    def _check_vercel(self, context: dict) -> dict:
        token = context.get("vercel_token") or os.getenv("VERCEL_TOKEN")
        team_id = context.get("vercel_team_id") or os.getenv("VERCEL_TEAM_ID")
        if not token:
            return {"check": "vercel_plan", "status": "no_configurado", "detail": "VERCEL_TOKEN ausente"}
        url = "https://api.vercel.com/v2/teams" + (f"/{team_id}" if team_id else "")
        try:
            data = self._http_get_json(url, {"Authorization": f"Bearer {token}"})
            plan = data.get("billing", {}).get("plan") or data.get("plan") or "desconocido"
            status = "ok_pago" if plan not in ("hobby", "", "desconocido") else "hobby_no_comercial"
            return {"check": "vercel_plan", "status": status, "detail": f"plan={plan}"}
        except Exception as exc:
            return {"check": "vercel_plan", "status": "error", "detail": str(exc)}

    def _check_render(self, context: dict) -> dict:
        api_key = context.get("render_api_key") or os.getenv("RENDER_API_KEY")
        service_ids = context.get("render_service_ids") or []
        if isinstance(service_ids, str):
            service_ids = [s.strip() for s in service_ids.split(",") if s.strip()]
        if not api_key:
            return {"check": "render_plan", "status": "no_configurado", "detail": "RENDER_API_KEY ausente"}
        if not service_ids:
            return {"check": "render_plan", "status": "no_configurado", "detail": "render_service_ids requerido en context"}
        plans = []
        for service_id in service_ids:
            try:
                data = self._http_get_json(
                    f"https://api.render.com/v1/services/{service_id}",
                    {"Authorization": f"Bearer {api_key}"},
                )
                plan = (data.get("serviceDetails") or {}).get("plan") or data.get("plan") or "desconocido"
                plans.append({"service_id": service_id, "plan": plan})
            except Exception as exc:
                plans.append({"service_id": service_id, "error": str(exc)})
        free_plans = [p for p in plans if str(p.get("plan", "")).lower() in ("free", "desconocido")]
        status = "pendiente" if free_plans or not plans else "ok_pago"
        return {"check": "render_plan", "status": status, "detail": plans}

    def _check_supabase(self, context: dict) -> dict:
        token = context.get("supabase_access_token") or os.getenv("SUPABASE_ACCESS_TOKEN")
        org_ids = context.get("supabase_org_ids") or []
        if isinstance(org_ids, str):
            org_ids = [s.strip() for s in org_ids.split(",") if s.strip()]
        if not token:
            return {"check": "supabase_plan", "status": "no_configurado", "detail": "SUPABASE_ACCESS_TOKEN ausente"}
        if not org_ids:
            try:
                orgs = self._http_get_json("https://api.supabase.com/v1/organizations", {"Authorization": f"Bearer {token}"})
                org_ids = [org.get("id") for org in orgs if org.get("id")]
            except Exception as exc:
                return {"check": "supabase_plan", "status": "error", "detail": str(exc)}
        info = []
        for org_id in org_ids:
            try:
                data = self._http_get_json(
                    f"https://api.supabase.com/v1/organizations/{org_id}",
                    {"Authorization": f"Bearer {token}"},
                )
                plan = data.get("plan") or "desconocido"
                info.append({"org_id": org_id, "name": data.get("name"), "plan": plan})
            except Exception as exc:
                info.append({"org_id": org_id, "error": str(exc)})
        free_plans = [p for p in info if str(p.get("plan", "")).lower() in ("free", "desconocido")]
        status = "pendiente" if free_plans or not info else "ok_pago"
        return {"check": "supabase_plan", "status": status, "detail": info}

    def _http_get_json(self, url: str, headers: dict) -> dict:
        req = urllib.request.Request(
            url,
            headers={**headers, "User-Agent": "FactoryFactory/0.1 (+https://github.com/)"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
