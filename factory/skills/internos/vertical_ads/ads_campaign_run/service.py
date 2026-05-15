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


class AdsCampaignRunService:
    """Thin campaign orchestrator that reuses company, marketing, ads and sales skills."""

    def ejecutar(self, context: dict) -> dict:
        company_id = str(context.get("company_id") or context.get("empresa_id") or "").strip()
        brief = context.get("brief") or context.get("campaign_brief") or context
        dry_run = context.get("dry_run", True)
        execute = bool(context.get("execute", False))

        company_context = _run("vertical_companies/company_context_builder", {
            "company_id": company_id,
            "config_path": context.get("config_path"),
            "brief": brief,
        })
        if not company_context.get("ok"):
            return company_context
        data = company_context["data"]
        campaign = data["campaign"]
        product = data["product"]

        activity_text = self._activity_text(data)
        skill_plan = _run("activity_skill_plan", {
            "actividad": activity_text,
            "lead_destination": "sales",
            "preset": campaign.get("lead_form_preset"),
            "campaign_name": campaign.get("campaign_name"),
            "daily_budget": self._daily_budget(campaign),
            "dry_run": True,
        })

        marketing_plan = _run("vertical_marketing/marketing_campaign_planner", {
            "objetivo": campaign.get("objective") or "leads",
            "producto": self._product_text(product),
            "audiencia": self._audience_text(data),
            "presupuesto": campaign.get("budget") or "no definido",
            "canales": ", ".join(campaign.get("channels") or []),
            "dry_run": True,
        })

        planned_payloads = self._planned_payloads(data, context)
        approval = _run("vertical_ads/ads_approval_queue_create", {
            "tipo_accion": "lanzar_campana",
            "campana": campaign.get("campaign_name"),
            "responsable": context.get("approver") or context.get("responsable") or "pendiente",
            "empresa_id": data["company"]["company_id"],
            "presupuesto": self._total_budget(campaign),
            "descripcion": "Aprobacion antes de crear o activar gasto publicitario.",
            "datos": {
                "campaign": campaign,
                "product": product,
                "planned_payloads": planned_payloads,
            },
        })

        result = {
            "company_context": data,
            "activity_plan": skill_plan.get("data") if skill_plan.get("ok") else {"error": skill_plan.get("error")},
            "marketing_plan": marketing_plan.get("data") if marketing_plan.get("ok") else {"error": marketing_plan.get("error")},
            "approval": approval.get("data") if approval.get("ok") else {"error": approval.get("error")},
            "planned_payloads": planned_payloads,
            "execution": {
                "dry_run": dry_run,
                "execute": execute,
                "status": "planned",
            },
        }

        if not execute:
            return {"ok": True, "data": result}

        if dry_run:
            result["execution"]["status"] = "dry_run_only"
            result["execution"]["message"] = "execute=true recibido, pero dry_run=true evita llamadas de escritura."
            return {"ok": True, "data": result}

        form_result = _run("vertical_meta_ads/meta_lead_form_create", planned_payloads["lead_form"])
        result["execution"]["lead_form_result"] = form_result
        if not form_result.get("ok"):
            result["execution"]["status"] = "failed_lead_form"
            return {"ok": False, "error": form_result.get("error"), "data": result}

        form_id = form_result.get("data", {}).get("form_id") or context.get("form_id")
        campaign_payload = {**planned_payloads["lead_campaign"], "form_id": form_id, "dry_run": False}
        campaign_result = _run("vertical_meta_ads/meta_ads_lead_campaign_flow", campaign_payload)
        result["execution"]["lead_campaign_result"] = campaign_result
        result["execution"]["status"] = "created" if campaign_result.get("ok") else "failed_campaign"
        return {"ok": campaign_result.get("ok", False), "error": campaign_result.get("error"), "data": result}

    def _activity_text(self, data: dict) -> str:
        campaign = data["campaign"]
        company = data["company"]
        return f"Crear campana Meta Lead Ads para {company.get('industry')} con destino sales: {campaign.get('campaign_name')}"

    def _planned_payloads(self, data: dict, context: dict) -> dict:
        campaign = data["campaign"]
        product = data["product"]
        daily_budget = float(context.get("daily_budget") or context.get("presupuesto_diario") or self._daily_budget(campaign))
        return {
            "lead_form": {
                "preset": campaign.get("lead_form_preset") or "custom",
                "form_name": context.get("form_name") or campaign.get("campaign_name"),
                "privacy_url": context.get("privacy_url"),
                "dry_run": True,
            },
            "lead_campaign": {
                "campaign_name": campaign.get("campaign_name"),
                "message": context.get("message") or self._message(product),
                "title": context.get("title") or "Solicita informacion",
                "description": context.get("description") or self._description(product),
                "daily_budget": daily_budget,
                "days": context.get("days") or context.get("dias") or 7,
                "status": campaign.get("initial_status") or "PAUSED",
                "targeting": context.get("targeting") or {"geo_locations": {"countries": ["MX"]}},
                "image_url": context.get("image_url"),
                "link": context.get("link") or product.get("landing_url"),
                "dry_run": True,
            },
            "leads_sync": {
                "empresa_id": data["company"]["company_id"],
                "form_id": context.get("form_id") or "<FORM_ID>",
                "dry_run": True,
            },
        }

    def _daily_budget(self, campaign: dict) -> float:
        budget = campaign.get("budget") or {}
        if isinstance(budget, dict):
            return float(
                budget.get("daily")
                or budget.get("daily_budget")
                or budget.get("presupuesto_diario")
                or campaign.get("minimum_daily_budget")
                or 0
            )
        try:
            value = float(budget)
            return value or float(campaign.get("minimum_daily_budget") or 0)
        except (TypeError, ValueError):
            return float(campaign.get("minimum_daily_budget") or 0)

    def _total_budget(self, campaign: dict) -> float:
        budget = campaign.get("budget") or {}
        if isinstance(budget, dict):
            return float(budget.get("total") or budget.get("presupuesto_total") or self._daily_budget(campaign))
        return self._daily_budget(campaign)

    def _product_text(self, product: dict) -> str:
        if not product:
            return "producto no especificado"
        parts = [f"{key}: {value}" for key, value in product.items() if value]
        return "; ".join(parts) or "producto no especificado"

    def _audience_text(self, data: dict) -> str:
        brief = data.get("raw_brief") or {}
        return str(brief.get("audience") or brief.get("audiencia") or data["company"].get("industry") or "audiencia por definir")

    def _message(self, product: dict) -> str:
        location = product.get("location") or product.get("zona") or "tu zona de interes"
        return f"Conoce esta opcion en {location}. Deja tus datos y un asesor te contacta."

    def _description(self, product: dict) -> str:
        benefits = product.get("main_benefits") or product.get("benefits") or []
        if isinstance(benefits, list):
            return ", ".join(str(item) for item in benefits[:3])
        return str(benefits or "")
