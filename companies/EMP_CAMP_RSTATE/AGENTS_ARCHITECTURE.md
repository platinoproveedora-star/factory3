# EMP_CAMP_RSTATE - Arquitectura de agentes

## Finalidad

EMP_CAMP_RSTATE es una instancia de empresa en Factory 3 para operar campanas de
real estate. No debe tener agentes ni skills exclusivos si la capacidad puede
servir a otras empresas. La unidad central es un agente orquestador generico que
lee `company.config.json`, coordina agentes especialistas genericos y adapta el
flujo al negocio inmobiliario.

## Principio de operacion

El orquestador no hace todo directamente. Recibe el objetivo de negocio, carga la
configuracion de la empresa, divide el trabajo, llama agentes especialistas,
valida entregables, pide aprobacion humana cuando hay riesgo y ejecuta las skills
tecnicas con `dry_run=True` por defecto hasta que la campana este aprobada.

## Separacion generico vs empresa

| Tipo | Donde vive | Ejemplo |
| --- | --- | --- |
| Agente reusable | `factory/agents` | `campaign_orchestrator_agent` |
| Skill reusable | `factory/skills/internos` | `vertical_ads/ads_campaign_run`, `vertical_sales/sales_run` |
| Bot reusable | `factory/bots` | `campaign_admin_bot` |
| Config de empresa | `companies/EMP_CAMP_RSTATE` | `company.config.json` |
| Preset particular | `companies/EMP_CAMP_RSTATE/presets` | Preguntas inmobiliarias, reglas de score |

## Agentes propuestos

| Agente generico | Rol | Adaptacion RSTATE | Skills principales | Estado |
| --- | --- | --- | --- |
| `campaign_orchestrator_agent` | Director de campana. Recibe brief, arma plan, reparte tareas, valida readiness y decide siguiente accion. | Lee `EMP_CAMP_RSTATE/company.config.json` | `activity_skill_plan`, `vertical_ads/ads_campaign_run`, `vertical_ads/ads_guardrails`, `vertical_ads/ads_report_generator` | Falta crear |
| `campaign_strategy_agent` | Define oferta, angulos, audiencia, funnel y presupuesto. | Usa industria `real_estate`, buyer profiles y umbrales de RSTATE | `vertical_marketing/marketing_campaign_planner`, `vertical_marketing/marketing_offer_builder`, `vertical_marketing/marketing_angle_generator`, `vertical_ads/ads_audience_builder`, `vertical_ads/ads_budget_planner` | Falta crear |
| `campaign_product_agent` | Convierte producto/servicio en ficha comercial lista para campana. | En RSTATE el producto es una propiedad o desarrollo | `buyer_persona_generator`, `brand_voice_analyzer`, `vertical_marketing/marketing_persona_builder` | Falta crear |
| `campaign_creative_agent` | Produce copies, briefs creativos, captions, carruseles y scripts. | Usa tono inmobiliario, CTA de visita/cotizacion y reglas de claims | `copy_generator`, `ad_creator`, `vertical_marketing/marketing_copy_generator`, `vertical_marketing/marketing_creative_brief`, `carousel_generator`, `vertical_instagram/ig_reel_script` | Falta crear |
| `campaign_asset_agent` | Prepara assets publicables: imagenes, carruseles, reels y URLs compatibles con Meta. | Usa fotos/renders/brochures de propiedad | `vertical_ads/ads_creative_validator`, `vertical_instagram/ig_carousel_builder`, `vertical_instagram/ig_alt_text_generator`, `supabase_storage_upload` | Parcial, faltan render/generacion real |
| `campaign_ads_agent` | Crea campana, adset, creative, anuncio y formulario en Meta Ads, siempre pausado al inicio. | Usa preset `inmobiliaria_venta_propiedades` | `vertical_meta_ads/meta_ads_connection_check`, `vertical_meta_ads/meta_lead_form_create`, `vertical_meta_ads/meta_ads_lead_campaign_flow`, `vertical_meta_ads/meta_ads_preview_ad` | Falta crear |
| `campaign_leads_agent` | Sincroniza leads, deduplica, califica y los mueve en pipeline. | Califica por presupuesto, zona, forma de compra y urgencia | `vertical_instagram/ig_lead_form_reads`, `vertical_sales/lead_pipeline_system`, `vertical_sales/lead_score_system`, `vertical_sales/sales_lead_update` | Falta crear |
| `campaign_followup_agent` | Genera seguimiento por canal, agenda visita/llamada y alerta al vendedor. | Agenda llamada, visita o tour | `vertical_sales/ai_followup_system`, `vertical_sales/automation_orchestrator_system`, `vertical_sales/sales_notify_agent`, `telegram_send_message` | Falta crear |
| `campaign_analytics_agent` | Lee performance y genera recomendaciones. | Reporta CPL, leads calificados, citas y costo por cita | `vertical_meta_ads/meta_ads_get_insights`, `vertical_meta_ads/meta_ads_dashboard_data`, `vertical_ads/ads_performance_analyzer`, `vertical_ads/ads_optimizer`, `vertical_marketing/marketing_report_generator` | Falta crear |
| `campaign_compliance_agent` | Revisa claims, presupuesto, tracking, permisos y riesgos antes de publicar o escalar. | Bloquea promesas como plusvalia garantizada o retorno garantizado | `vertical_ads/ads_campaign_preflight_check`, `vertical_marketing/marketing_compliance_checker`, `vertical_ads/ads_guardrails`, `vertical_ads/ads_creative_validator`, `vertical_meta_ads/meta_ads_pixel_check` | Falta crear |

## Flujo principal

| Paso | Responsable | Entrada | Salida |
| --- | --- | --- | --- |
| 1 | Orquestador | Brief de campana, propiedad, presupuesto, ciudad, objetivo | Plan de trabajo y checklist |
| 2 | Property Agent | Datos de propiedad/desarrollo | Ficha comercial normalizada |
| 3 | Strategy Agent | Ficha comercial + objetivo | Audiencia, oferta, funnel y presupuesto |
| 4 | Creative Agent | Estrategia | Copy, hooks, CTA, captions y brief visual |
| 5 | Media Agent | Brief visual + assets | Assets validados o pendientes |
| 6 | Ads Agent | Estrategia + copy + assets | Campana Meta Ads en `PAUSED` y preview |
| 7 | Compliance Agent | Preview + config + presupuesto | Aprobado, bloqueado o requiere humano |
| 8 | Orquestador | Decision humana | Activar, pausar o corregir |
| 9 | Leads Agent | Leads de formularios | Leads en pipeline inmobiliario |
| 10 | Followup Agent | Leads calificados | Seguimientos y citas |
| 11 | Analytics Agent | Insights + pipeline | Reporte y recomendaciones |

## Skills que hacen falta para RSTATE

| Skill generico faltante | Tipo | Prioridad | Motivo |
| --- | --- | --- | --- |
| `vertical_ads/ads_campaign_run` | Orquestador skill | Alta | Punto unico para crear campana completa con agentes y skills |
| `vertical_companies/company_config_loader` | Config skill | Alta | Cargar `company.config.json` de cualquier empresa |
| `vertical_companies/company_context_builder` | Context skill | Alta | Mezclar brief + config + defaults de empresa |
| `product_profile_store` | Data skill | Alta | Guardar producto/servicio; en RSTATE sera propiedad/desarrollo |
| `offer_builder` | Marketing skill | Alta | Convertir producto en oferta clara para ads |
| `vertical_sales/lead_score_system` | Sales skill | Ya existe | Calificar leads con reglas/base de ventas |
| `vertical_meta_ads/meta_leads_sync_to_sales` | Integration skill | Alta | Sincronizar leads Meta hacia pipeline de ventas generico |
| `appointment_scheduler` | Sales skill | Media | Agendar llamada, visita, demo o tour segun empresa |
| `campaign_dashboard_data` | Data skill | Media | Dashboard especifico por empresa usando KPIs configurados |
| `asset_generator` | Creative skill | Media | Crear assets visuales reales segun tipo de producto |
| `campaign_memory` | Memory schema | Media | Guardar aprendizajes por campana, empresa e industria |

## Datos minimos de una campana

| Campo | Descripcion |
| --- | --- |
| `company_id` | `EMP_CAMP_RSTATE` |
| `campaign_goal` | Leads, mensajes, visitas, preventa, renta o venta |
| `property_type` | Casa, departamento, lote, local, desarrollo, oficina |
| `location` | Ciudad, colonia, zona o radio |
| `price_range` | Precio, renta o rango |
| `buyer_profile` | Primer hogar, inversionista, familia, lujo, renta, extranjero |
| `budget` | Presupuesto total y diario |
| `channels` | Meta Ads, Instagram, Facebook, grupos, marketplace |
| `assets` | Fotos, videos, renders, logo, brochure, landing |
| `approval_required` | Default `true` |

## Primer MVP recomendado

1. Crear `rstate_orchestrator_agent` y registrarlo.
2. Usar `vertical_ads/ads_campaign_run` como skill orquestador en modo `dry_run`.
3. Usar el preset existente `inmobiliaria_venta_propiedades` para Lead Ads.
4. Crear campana Meta Ads pausada.
5. Sincronizar leads a un pipeline RSTATE basado en `vertical_sales`.
6. Mostrar reporte simple de gasto, leads, CPL y citas.

## Adaptacion RSTATE

La adaptacion particular vive en `company.config.json`:

- Industria: `real_estate`
- Producto: `property`
- Preset de formulario: `inmobiliaria_venta_propiedades`
- Pipeline: nuevo, contactado, calificado, cita, visita, propuesta, cierre, perdido
- Score: presupuesto, zona, tiempo de compra, forma de compra y credito preaprobado
- Compliance: bloquear promesas de plusvalia garantizada, retorno garantizado o credito para todos
