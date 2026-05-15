# vertical_ads/campaign_launch_paused

Lanza el flujo seguro de campana pagada. Requiere `form_id` ya creado.

Por defecto hace `dry_run`. Si `execute=true`, fuerza `status=PAUSED` y llama
`vertical_meta_ads/meta_ads_lead_campaign_flow`.
