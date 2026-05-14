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


class CompanyContextBuilderService:
    """Builds an operational campaign context from a company config and a brief."""

    def ejecutar(self, context: dict) -> dict:
        company_id = str(context.get("company_id") or context.get("empresa_id") or "").strip()
        brief = context.get("brief") or context.get("campaign_brief") or {}
        if isinstance(brief, str):
            brief = {"raw": brief}
        if not isinstance(brief, dict):
            return {"ok": False, "error": "brief debe ser dict o texto"}

        loaded = _run("vertical_companies/company_config_loader", {
            "company_id": company_id,
            "config_path": context.get("config_path"),
        })
        if not loaded.get("ok"):
            return loaded

        config = loaded["data"]["config"]
        defaults = config.get("campaign_defaults") or {}
        product_schema = config.get("product_schema") or {}
        lead_schema = config.get("lead_schema") or {}
        reporting = config.get("reporting") or {}

        campaign = {
            "company_id": config.get("company_id"),
            "company_name": config.get("company_name"),
            "industry": config.get("industry"),
            "objective": brief.get("objective") or brief.get("objetivo") or defaults.get("objective") or "leads",
            "campaign_name": brief.get("campaign_name") or brief.get("nombre_campana") or self._default_campaign_name(config, brief),
            "budget": brief.get("budget") or brief.get("presupuesto") or {},
            "channels": brief.get("channels") or brief.get("canales") or config.get("channels") or [],
            "approval_required": brief.get("approval_required", defaults.get("approval_required", True)),
            "initial_status": brief.get("initial_status") or defaults.get("initial_status") or "PAUSED",
            "lead_form_preset": brief.get("lead_form_preset") or defaults.get("lead_form_preset"),
            "currency": brief.get("currency") or defaults.get("currency"),
            "minimum_daily_budget": defaults.get("minimum_daily_budget"),
            "recommended_test_days": defaults.get("recommended_test_days"),
        }

        product = brief.get("product") or brief.get(product_schema.get("product_label", "product")) or brief.get("property") or {}
        if isinstance(product, str):
            product = {"description": product}

        missing_product_fields = self._missing(product, product_schema.get("required_fields") or [])
        lead_qualification = config.get("lead_qualification") or {}

        return {
            "ok": True,
            "data": {
                "company": {
                    "company_id": config.get("company_id"),
                    "company_name": config.get("company_name"),
                    "company_type": config.get("company_type"),
                    "industry": config.get("industry"),
                },
                "config_path": loaded["data"]["config_path"],
                "agent_stack": config.get("agent_stack") or {},
                "skill_stack": config.get("skill_stack") or {},
                "campaign": campaign,
                "product": product,
                "lead_schema": lead_schema,
                "lead_qualification": lead_qualification,
                "pipeline": config.get("pipeline") or {},
                "compliance": config.get("compliance") or {},
                "reporting": reporting,
                "readiness": {
                    "ready": not missing_product_fields,
                    "missing_product_fields": missing_product_fields,
                    "approval_required": campaign["approval_required"],
                },
                "raw_brief": brief,
            },
        }

    def _default_campaign_name(self, config: dict, brief: dict) -> str:
        product = brief.get("property") or brief.get("product") or {}
        location = ""
        if isinstance(product, dict):
            location = product.get("location") or product.get("zona") or ""
        industry = config.get("industry") or "campaign"
        suffix = f" - {location}" if location else ""
        return f"{config.get('company_id', 'COMPANY')} {industry} leads{suffix}"

    def _missing(self, data: dict, required: list[str]) -> list[str]:
        return [field for field in required if not data.get(field)]
