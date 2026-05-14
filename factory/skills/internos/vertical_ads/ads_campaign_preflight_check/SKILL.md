---
name: vertical_ads/ads_campaign_preflight_check
vertical: vertical_ads
type: internal
entrypoint: skill.py
contract: run(context) -> dict
---

# ads_campaign_preflight_check

Gate pre-lanzamiento para campanas pagadas. Valida que la campana este lista
antes de crearla o activarla.

Puede recibir:

- `campaign_run_result` o `plan`: resultado de `vertical_ads/ads_campaign_run`.
- `company_id` + `brief`: ejecuta internamente `ads_campaign_run` en `dry_run`.

Devuelve:

- `ready_to_launch`
- `risk_score`
- `risk_level`
- `blockers`
- `warnings`
- `recommended_next_actions`
