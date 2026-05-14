# Dashboard Campaign Ops

Modulo generico de dashboard para operar campanas de cualquier empresa.

## Objetivo

Dar una rama reutilizable de menu para:

- revisar la campana actual
- subir fotos/assets
- correr preflight
- ver resultados de ads
- ver leads y pipeline
- documentar pendientes antes de lanzar

La empresa se adapta por `company_id` y por `company.config.json`.

## Menu recomendado

```text
Campaign Ops
  Overview
  Campaign 1
  Uploads
  Preflight
  Leads
  Results
  Settings
```

## Secciones

| Menu | Funcion | Skills / datos |
| --- | --- | --- |
| `Overview` | KPIs generales de campanas y readiness. | `vertical_ads/ads_campaign_preflight_check`, `vertical_meta_ads/meta_ads_dashboard_data` |
| `Campaign 1` | Ficha de campana, payloads, copy, status, presupuesto. | `vertical_ads/ads_campaign_run` |
| `Uploads` | Subir fotos/renders/assets y obtener URLs publicas. | `supabase_storage_upload` |
| `Preflight` | Gate antes de lanzar: blockers, warnings, riesgo. | `vertical_ads/ads_campaign_preflight_check` |
| `Leads` | Leads recibidos, score, pipeline y tareas. | `vertical_sales/sales_list`, `vertical_sales/sales_report` |
| `Results` | Gasto, impresiones, clicks, CPL, CTR, recomendaciones. | `vertical_meta_ads/meta_ads_get_insights`, `vertical_ads/ads_performance_analyzer` |
| `Settings` | Empresa, campana, presupuesto, links, privacy URL, contacto. | `vertical_companies/company_config_loader` |

## Datos minimos para que Uploads funcione

| Dato | Uso |
| --- | --- |
| `SUPABASE_URL` | Conectar a Supabase |
| `SUPABASE_SERVICE_ROLE_KEY` | Subir/leer assets |
| `bucket` | Bucket publico de assets |
| `company_id` | Carpeta logica de empresa |
| `campaign_id` | Carpeta logica de campana |

## Estructura sugerida en storage

```text
campaign-assets/
  EMP_CAMP_RSTATE/
    first_rstate_campaign/
      hero.jpg
      office-1.jpg
      lobby.jpg
```

## Campos que el dashboard debe administrar

| Campo | Descripcion |
| --- | --- |
| `privacy_url` | URL del aviso de privacidad |
| `image_url` | Imagen principal del anuncio |
| `link` | Landing, WhatsApp o ficha publica |
| `whatsapp_number` | Numero destino del CTA |
| `approver` | Responsable de aprobacion |
| `campaign_name` | Nombre operativo de campana |
| `form_id` | ID del Lead Form despues de crearlo |
| `campaign_id` | ID Meta Ads despues de crear campana |

## Plantilla Streamlit

La plantilla generica vive en:

```text
factory/dashboard_modules/campaign_ops.py
```

Se puede usar desde un dashboard Streamlit existente:

```python
from factory.dashboard_modules.campaign_ops import render_campaign_ops

render_campaign_ops(
    run_skill=_run_skill,
    company_id="EMP_CAMP_RSTATE",
    campaign_slug="first_rstate_campaign",
)
```

`_run_skill` debe ser una funcion local del dashboard compatible con:

```python
def _run_skill(nombre: str, context: dict, source: str = "internos") -> dict:
    ...
```

## Para EMP_CAMP_RSTATE

Primera campana:

```text
companies/EMP_CAMP_RSTATE/first_rstate_campaign.md
```

Blockers actuales:

- falta `privacy_url`
- falta `image_url`
- falta `link` o WhatsApp/landing para tracking
