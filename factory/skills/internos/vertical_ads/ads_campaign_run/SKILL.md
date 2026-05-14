---
name: vertical_ads/ads_campaign_run
vertical: vertical_ads
type: internal
entrypoint: skill.py
contract: run(context) -> dict
---

# ads_campaign_run

Orquestador delgado para campanas pagadas. No reemplaza a los skills existentes:
los coordina. Por defecto devuelve plan, payloads y aprobacion en `dry_run`.

Usa:

- `vertical_companies/company_context_builder`
- `activity_skill_plan`
- `vertical_marketing/marketing_campaign_planner`
- `vertical_ads/ads_approval_queue_create`
- `vertical_meta_ads/meta_lead_form_create`
- `vertical_meta_ads/meta_ads_lead_campaign_flow`
