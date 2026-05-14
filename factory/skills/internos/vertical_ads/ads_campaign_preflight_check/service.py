from __future__ import annotations

from pathlib import Path


def _runner():
    from factory.engine import SkillLoader, SkillRunner

    root = Path(__file__).resolve().parents[2]
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


class AdsCampaignPreflightCheckService:
    """Pre-launch gate for paid campaigns.

    Accepts either a previous `vertical_ads/ads_campaign_run` result in
    `campaign_run_result`/`plan` or a fresh `company_id + brief` payload.
    """

    def ejecutar(self, context: dict) -> dict:
        plan = context.get("campaign_run_result") or context.get("plan")
        if isinstance(plan, dict) and "data" in plan:
            plan = plan.get("data")

        if not isinstance(plan, dict):
            run_result = _run("vertical_ads/ads_campaign_run", {
                "company_id": context.get("company_id") or context.get("empresa_id"),
                "config_path": context.get("config_path"),
                "brief": context.get("brief") or context.get("campaign_brief") or context,
                "message": context.get("message"),
                "title": context.get("title"),
                "description": context.get("description"),
                "image_url": context.get("image_url"),
                "link": context.get("link"),
                "privacy_url": context.get("privacy_url"),
                "approver": context.get("approver") or context.get("responsable"),
                "dry_run": True,
                "execute": False,
            })
            if not run_result.get("ok"):
                return run_result
            plan = run_result["data"]

        company_context = plan.get("company_context") or {}
        campaign = company_context.get("campaign") or {}
        product = company_context.get("product") or {}
        compliance_config = company_context.get("compliance") or {}
        reporting = company_context.get("reporting") or {}
        planned_payloads = plan.get("planned_payloads") or {}
        lead_form = planned_payloads.get("lead_form") or {}
        lead_campaign = planned_payloads.get("lead_campaign") or {}
        leads_sync = planned_payloads.get("leads_sync") or {}
        approval = plan.get("approval") or {}

        checks = []
        checks.extend(self._context_checks(company_context, campaign, product))
        checks.extend(self._asset_checks(lead_form, lead_campaign))
        checks.extend(self._lead_flow_checks(lead_form, leads_sync))
        checks.extend(self._approval_checks(approval, campaign))
        checks.extend(self._kpi_checks(campaign, reporting))
        checks.extend(self._claim_checks(lead_campaign, compliance_config))
        checks.append(self._guardrails_check(campaign, lead_campaign, context))
        creative_check = self._creative_check(context)
        if creative_check:
            checks.append(creative_check)

        blockers = [item for item in checks if item["severity"] == "blocker" and not item["passed"]]
        warnings = [item for item in checks if item["severity"] == "warning" and not item["passed"]]
        passed = [item for item in checks if item["passed"]]
        risk_score = self._risk_score(blockers, warnings)
        risk_level = "critico" if risk_score >= 80 else "alto" if risk_score >= 50 else "medio" if risk_score >= 20 else "bajo"

        return {
            "ok": True,
            "data": {
                "ready_to_launch": len(blockers) == 0,
                "risk_score": risk_score,
                "risk_level": risk_level,
                "summary": {
                    "checks_total": len(checks),
                    "passed": len(passed),
                    "blockers": len(blockers),
                    "warnings": len(warnings),
                },
                "blockers": blockers,
                "warnings": warnings,
                "checks": checks,
                "recommended_next_actions": self._next_actions(blockers, warnings),
                "campaign": {
                    "company_id": campaign.get("company_id"),
                    "campaign_name": campaign.get("campaign_name"),
                    "status": lead_campaign.get("status"),
                    "daily_budget": lead_campaign.get("daily_budget"),
                    "total_budget": self._total_budget(campaign),
                },
            },
        }

    def _context_checks(self, company_context: dict, campaign: dict, product: dict) -> list[dict]:
        readiness = company_context.get("readiness") or {}
        missing = readiness.get("missing_product_fields") or []
        return [
            self._check("company_context", bool(company_context), "Contexto de empresa disponible", "blocker"),
            self._check("product_required_fields", not missing, f"Campos requeridos completos; faltantes: {missing}", "blocker"),
            self._check("campaign_objective", bool(campaign.get("objective")), "Objetivo de campana definido", "blocker"),
            self._check("product_data", bool(product), "Datos de producto/propiedad disponibles", "blocker"),
        ]

    def _asset_checks(self, lead_form: dict, lead_campaign: dict) -> list[dict]:
        return [
            self._check("privacy_url", bool(lead_form.get("privacy_url")), "URL de privacidad requerida para Lead Form", "blocker"),
            self._check("creative_image_url", bool(lead_campaign.get("image_url")), "Imagen/render publico para el anuncio", "blocker"),
            self._check("destination_link", bool(lead_campaign.get("link")), "Landing/link opcional pero recomendado", "warning"),
            self._check("ad_message", bool(lead_campaign.get("message")), "Copy principal definido", "blocker"),
            self._check("ad_title", bool(lead_campaign.get("title")), "Titulo del anuncio definido", "blocker"),
        ]

    def _lead_flow_checks(self, lead_form: dict, leads_sync: dict) -> list[dict]:
        return [
            self._check("lead_form_preset", bool(lead_form.get("preset")), "Preset o preguntas del formulario definido", "blocker"),
            self._check("lead_sync_company", bool(leads_sync.get("empresa_id")), "Sync de leads tiene empresa destino", "blocker"),
            self._check("lead_sync_form_placeholder", bool(leads_sync.get("form_id")), "Sync preparado para recibir form_id", "warning"),
        ]

    def _approval_checks(self, approval: dict, campaign: dict) -> list[dict]:
        required = bool(campaign.get("approval_required", True))
        status = approval.get("estado") or approval.get("payload", {}).get("estado")
        return [
            self._check("approval_created", bool(approval), "Solicitud de aprobacion creada", "blocker" if required else "warning"),
            self._check("approval_status", status in {"pendiente", "aprobado"}, f"Estado de aprobacion valido: {status}", "warning"),
        ]

    def _kpi_checks(self, campaign: dict, reporting: dict) -> list[dict]:
        thresholds = reporting.get("optimization_thresholds") or {}
        daily = self._daily_budget(campaign)
        total = self._total_budget(campaign)
        minimum = float(campaign.get("minimum_daily_budget") or 0)
        return [
            self._check("daily_budget", daily >= minimum > 0, f"Presupuesto diario {daily} >= minimo {minimum}", "blocker"),
            self._check("total_budget", total >= daily > 0, f"Presupuesto total {total} >= diario {daily}", "blocker"),
            self._check("kpi_max_cpl", bool(thresholds.get("max_cpl")), "CPL maximo definido para optimizacion", "warning"),
            self._check("kpi_min_ctr", bool(thresholds.get("min_ctr")), "CTR minimo definido para optimizacion", "warning"),
        ]

    def _claim_checks(self, lead_campaign: dict, compliance_config: dict) -> list[dict]:
        copy = " ".join(
            str(lead_campaign.get(key) or "")
            for key in ("message", "title", "description")
        ).lower()
        blocked_claims = compliance_config.get("blocked_claims") or []
        hits = [claim for claim in blocked_claims if claim.lower() in copy]
        sensitive = compliance_config.get("requires_human_approval") or []
        investment_terms = ["renta", "inquilino", "inversion", "mensual"]
        needs_review = any(term in copy for term in investment_terms) and bool(sensitive)
        return [
            self._check("blocked_claims", not hits, f"Claims bloqueados detectados: {hits}", "blocker"),
            self._check("sensitive_claim_review", not needs_review, "Claims de inversion/renta requieren revision humana", "warning"),
        ]

    def _guardrails_check(self, campaign: dict, lead_campaign: dict, context: dict) -> dict:
        result = _run("vertical_ads/ads_guardrails", {
            "campana": campaign.get("campaign_name") or lead_campaign.get("campaign_name") or "campana",
            "presupuesto_diario": self._daily_budget(campaign),
            "presupuesto_total": self._total_budget(campaign),
            "presupuesto_gastado": context.get("presupuesto_gastado", 0),
            "tiene_pixel": bool(context.get("tiene_pixel", False)),
            "tiene_tracking": bool(context.get("tiene_tracking", bool(lead_campaign.get("link")))),
            "ctr": context.get("ctr", 0),
            "roas": context.get("roas", 0),
            "frecuencia": context.get("frecuencia", 0),
            "dias_sin_conversion": context.get("dias_sin_conversion", 0),
        })
        if not result.get("ok"):
            return self._check("ads_guardrails", False, result.get("error", "guardrails error"), "warning")
        data = result.get("data") or {}
        passed = bool(data.get("aprobado"))
        # For lead-form campaigns a missing pixel is important, but not always a hard blocker.
        severity = "warning" if data.get("bloqueos") else "info"
        return self._check("ads_guardrails", passed, data.get("accion", "Guardrails evaluados"), severity, data)

    def _creative_check(self, context: dict) -> dict | None:
        creative = context.get("creative") or context.get("asset")
        if not isinstance(creative, dict):
            return None
        result = _run("vertical_ads/ads_creative_validator", {
            "plataforma": creative.get("plataforma") or "meta",
            "formato": creative.get("formato") or "imagen",
            "proporcion": creative.get("proporcion") or "",
            "peso_mb": creative.get("peso_mb"),
            "duracion_s": creative.get("duracion_s"),
            "extension": creative.get("extension") or "",
            "texto_pct": creative.get("texto_pct"),
        })
        if not result.get("ok"):
            return self._check("creative_validator", False, result.get("error", "creative validator error"), "warning")
        data = result.get("data") or {}
        return self._check("creative_validator", bool(data.get("aprobado")), "Asset cumple specs declaradas", "blocker", data)

    def _check(self, code: str, passed: bool, message: str, severity: str, details: dict | None = None) -> dict:
        return {
            "code": code,
            "passed": bool(passed),
            "severity": severity,
            "message": message,
            "details": details or {},
        }

    def _daily_budget(self, campaign: dict) -> float:
        budget = campaign.get("budget") or {}
        if isinstance(budget, dict):
            value = budget.get("daily") or budget.get("daily_budget") or budget.get("presupuesto_diario")
        else:
            value = budget
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0

    def _total_budget(self, campaign: dict) -> float:
        budget = campaign.get("budget") or {}
        if isinstance(budget, dict):
            value = budget.get("total") or budget.get("presupuesto_total") or self._daily_budget(campaign)
        else:
            value = budget
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0

    def _risk_score(self, blockers: list[dict], warnings: list[dict]) -> int:
        return min(100, len(blockers) * 25 + len(warnings) * 8)

    def _next_actions(self, blockers: list[dict], warnings: list[dict]) -> list[str]:
        actions = []
        mapping = {
            "privacy_url": "Agregar privacy_url antes de crear el Lead Form real.",
            "creative_image_url": "Agregar image_url publica de foto/render del anuncio.",
            "destination_link": "Agregar landing, WhatsApp o ficha publica si se usara tracking.",
            "blocked_claims": "Corregir copy para eliminar claims bloqueados.",
            "daily_budget": "Ajustar presupuesto diario al minimo configurado.",
            "approval_created": "Crear o asignar aprobacion humana.",
        }
        for item in blockers + warnings:
            action = mapping.get(item["code"])
            if action and action not in actions:
                actions.append(action)
        if not actions:
            actions.append("Sin bloqueos; revisar aprobacion humana y crear campana en PAUSED.")
        return actions
