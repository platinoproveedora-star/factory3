# Patron de empresas en Factory 3

## Idea central

Las empresas no deben duplicar agentes ni skills cuando el proceso es el mismo.
Factory debe tener agentes, bots y skills genericos por capacidad; cada empresa
solo define configuracion, presets, reglas, credenciales, prompts de negocio y
tablas/colecciones propias.

## Capas

| Capa | Vive en | Que contiene | Ejemplo |
| --- | --- | --- | --- |
| Motor generico | `factory/skills/internos` | Skills reutilizables por cualquier empresa | `vertical_meta_ads/meta_ads_lead_campaign_flow` |
| Agentes genericos | `factory/agents` | Roles reutilizables que orquestan skills | `campaign_orchestrator_agent` |
| Bots genericos | `factory/bots` | Entrada conversacional configurable | `campaign_admin_bot` |
| Empresa | `companies/<EMPRESA>` | Config, presets, reglas, schemas y memoria | `EMP_CAMP_RSTATE` |

## Regla de diseno

Si algo sirve para varias empresas, va al motor generico. Si algo solo cambia
por cliente, industria, tono, presupuesto, canal o campos, va a config de empresa.

## Agentes genericos recomendados

| Agente generico | Responsabilidad | Adaptacion por empresa |
| --- | --- | --- |
| `campaign_orchestrator_agent` | Dirige la campana completa y coordina agentes. | `company_id`, vertical, checklist, aprobaciones |
| `campaign_strategy_agent` | Oferta, audiencia, funnel, presupuesto y plan. | Tipo de negocio, buyer personas, restricciones |
| `campaign_asset_agent` | Brief creativo, assets, validacion y formatos. | Brand kit, ejemplos, tipo de producto |
| `campaign_ads_agent` | Configura y publica campanas pagadas. | Cuentas Meta, presets, presupuesto, objetivos |
| `campaign_leads_agent` | Captura, deduplica, califica y enruta leads. | Campos de lead, score, pipeline |
| `campaign_followup_agent` | Seguimiento, citas y notificaciones. | Mensajes, SLA, canales, vendedores |
| `campaign_analytics_agent` | Reporta performance y recomienda optimizacion. | KPIs por empresa, umbrales, tablero |
| `campaign_compliance_agent` | Revisa claims, gasto, tracking y riesgos. | Politicas de industria y reglas del cliente |

## Skills genericos que deberian existir

| Skill generico | Funcion | Config que consume |
| --- | --- | --- |
| `vertical_ads/ads_campaign_run` | Orquesta una campana end-to-end. | `company.config.json` |
| `vertical_companies/company_config_loader` | Carga config de empresa y la normaliza. | Ruta o `company_id` |
| `vertical_companies/company_context_builder` | Construye contexto de campana para agentes. | Brief + config |
| `vertical_sales/lead_score_system` | Califica leads dentro del flujo de ventas. | `lead_qualification` |
| `vertical_meta_ads/meta_leads_sync_to_sales` | Enruta leads Meta hacia ventas. | `pipeline.stages` |
| `campaign_dashboard_data` | Devuelve metricas filtradas por empresa. | `reporting.kpis` |
| `asset_public_url` | Sube/normaliza assets para publicar. | `assets.storage` |

## Estructura minima de una empresa

```
companies/<EMPRESA>/
  company.config.json
  AGENTS_ARCHITECTURE.md
  schemas/
  presets/
  prompts/
  dashboards/
```

## Contrato minimo de `company.config.json`

| Campo | Uso |
| --- | --- |
| `company_id` | Identificador unico de empresa |
| `company_type` | Tipo de operacion, por ejemplo `campaigns` |
| `industry` | Industria, por ejemplo `real_estate` |
| `agent_stack` | Agentes genericos que se usan |
| `skill_stack` | Skills genericos y verticales habilitados |
| `channels` | Canales permitidos |
| `campaign_defaults` | Presupuesto, objetivo, status inicial, aprobaciones |
| `lead_schema` | Campos esperados para capturar leads |
| `lead_qualification` | Reglas de score y filtros |
| `pipeline` | Etapas operativas |
| `compliance` | Reglas y frases prohibidas |
| `reporting` | KPIs y umbrales |
