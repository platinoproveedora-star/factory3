# Campaign Automation Roadmap

Objetivo: crear una campana completa desde cero con la menor intervencion
manual posible: empresa, dashboard, landing, assets, Render, preflight, Meta y
leads.

## Estado actual

| Bloque | Estado | Notas |
| --- | --- | --- |
| Empresa/config | Funciona | `vertical_companies/company_config_loader` y `company_context_builder`. |
| Dashboard | Funciona | `company_dashboard_scaffold` y dashboard RSTATE en Render. |
| Upload assets | Funciona | `supabase_storage_upload` con bucket `campaign-assets`. |
| Landing dinamica | En progreso | Landing lee `landing_config.json`; dashboard ya puede guardar datos/fotos. |
| Preflight | Funciona en dry run | `vertical_ads/ads_campaign_preflight_check` ya dio ready. |
| Meta real | Pendiente | Falta probar create lead form/campaign real en `PAUSED`. |
| Leads reales | Pendiente | Falta probar sync Meta Leads -> Sales. |

## Skills que ya existen

| Skill | Uso |
| --- | --- |
| `vertical_companies/company_config_loader` | Cargar config por empresa. |
| `vertical_companies/company_context_builder` | Normalizar brief + empresa. |
| `vertical_companies/company_dashboard_scaffold` | Crear dashboard base con Campaign Ops. |
| `vertical_marketing/marketing_privacy_notice_builder` | Generar aviso de privacidad. |
| `vertical_marketing/marketing_mini_landing_scaffold` | Crear landing inicial. |
| `vertical_ads/ads_campaign_preflight_check` | Validar blockers/warnings antes de lanzar. |
| `vertical_ads/ads_campaign_run` | Generar payloads de campana en dry run. |
| `vertical_meta_ads/meta_lead_form_create` | Crear formulario de leads Meta. Pendiente real. |
| `vertical_meta_ads/meta_ads_lead_campaign_flow` | Crear campana Meta Lead Ads. Pendiente real. |
| `vertical_meta_ads/meta_leads_sync_to_sales` | Sincronizar leads a Sales. Pendiente real. |

## Skills faltantes recomendados

| Skill propuesto | Responsabilidad |
| --- | --- |
| `vertical_marketing/property_landing_config_builder` | Crear/actualizar `landing_config.json` desde brief de propiedad. |
| `vertical_marketing/property_landing_renderer` | Mantener plantilla HTML dinamica para inmuebles. |
| `vertical_marketing/campaign_asset_manager` | Listar, elegir, borrar y marcar imagen principal/galeria. |
| `vertical_render/render_landing_publish` | Crear o actualizar servicio Render para landing. |
| `vertical_ads/campaign_config_writer` | Guardar `image_url`, `privacy_url`, `link`, `approver` en JSON de campana. |
| `vertical_meta_ads/meta_ad_account_finder` | Listar/adivinar/validar `META_AD_ACCOUNT_ID`. |
| `vertical_ads/campaign_launch_paused` | Crear campana real siempre en `PAUSED` y registrar IDs. |
| `vertical_sales/lead_intake_from_meta` | Recibir leads Meta y normalizarlos a Sales. |

## Flujo objetivo

```text
1. Crear empresa/campana
2. Generar dashboard configurable
3. Generar landing dinamica
4. Publicar landing en Render
5. Subir fotos y guardar landing_config.json
6. Correr preflight
7. Crear lead form real
8. Crear campana real en PAUSED
9. Revisar con humano/broker
10. Activar campana
11. Sincronizar leads a Sales
12. Leer resultados e insights
```

## Regla de seguridad

Toda campana real debe crearse primero en `PAUSED`. La activacion debe requerir
aprobacion humana con responsable (`approver`) y revision de presupuesto, copy,
imagenes, privacy URL y destino.
