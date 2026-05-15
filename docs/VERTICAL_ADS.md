# vertical_ads

Vertical de operacion publicitaria generica. Contiene skills para audiencias,
presupuestos, aprobaciones, guardrails, optimizacion y orquestacion de campanas.

## Orquestador

### `vertical_ads/ads_campaign_run`

Orquestador delgado de campanas pagadas. No duplica los skills existentes: los
coordina usando configuracion de empresa.

Flujo MVP:

```
vertical_companies/company_context_builder
-> activity_skill_plan
-> vertical_marketing/marketing_campaign_planner
-> vertical_ads/ads_approval_queue_create
-> vertical_ads/ads_campaign_preflight_check
-> vertical_ads/campaign_config_writer
-> vertical_ads/campaign_launch_paused
-> vertical_meta_ads/meta_lead_form_create
-> vertical_meta_ads/meta_ads_lead_campaign_flow
-> vertical_meta_ads/meta_leads_sync_to_sales
```

Por defecto no escribe ni publica. Devuelve plan y payloads con `dry_run=True`.
Para ejecutar llamadas reales se requiere `execute=true` y `dry_run=false`; aun
asi la campana Meta se crea en `PAUSED` salvo que un skill de Meta Ads permita
otro estado explicitamente.

### `vertical_ads/ads_campaign_preflight_check`

Gate previo a lanzamiento. Puede recibir el resultado de `ads_campaign_run` o
un `company_id + brief`; valida:

- config de empresa y campos requeridos
- privacy URL, imagen, link, copy y titulo
- presupuesto diario/total contra umbrales
- claims bloqueados y necesidad de revision humana
- aprobacion
- KPIs esperados
- flujo de leads hacia ventas
- guardrails basicos

Devuelve `ready_to_launch`, `risk_score`, `blockers`, `warnings` y siguientes
acciones recomendadas.

### `vertical_ads/campaign_config_writer`

Actualiza el JSON de una campana dentro de `companies/<COMPANY_ID>/` con los
campos operativos que se van confirmando desde dashboard: landing, imagen,
privacy URL, WhatsApp, approver, presupuesto e IDs de Meta.

### `vertical_ads/campaign_launch_paused`

Wrapper de seguridad para crear o preparar una campana Meta Lead Ads. Requiere
`form_id`, corre preflight y fuerza `status=PAUSED`. Por defecto hace dry run;
para crear en Meta debe recibirse `execute=true`.
