# vertical_meta_ads

Automatiza campanas Meta Ads. La vertical debe mantenerse generica: los casos
de empresa, oferta, vacante o producto se pasan como payload o presets.

## Flujo MVP

```
meta_ads_connection_check
-> meta_lead_form_create
-> meta_ads_lead_campaign_flow
-> meta_leads_sync_to_rh / sync especifico de vertical
```

Todo el flujo de publicacion crea campana, adset, creativo y anuncio en `PAUSED`
por seguridad.

## Skills clave

- `meta_ads_connection_check` - valida token y cuenta publicitaria.
- `meta_lead_form_create` - crea Instant Form desde preset o preguntas custom.
- `meta_ads_lead_campaign_flow` - crea campana Lead Ads generica pausada.
- `meta_leads_sync_to_rh` - lee leads del formulario y crea candidatos RH.
- `meta_leads_sync_to_sales` - lee leads del formulario y los enruta a `vertical_sales/sales_run`.
- `meta_ads_get_insights` - consulta metricas de campana/adset/ad.
- `meta_ads_update_campaign` - activa, pausa o renombra campanas.

## Variables requeridas

```
META_ACCESS_TOKEN=
META_AD_ACCOUNT_ID=
META_PAGE_ID=
META_PRIVACY_URL=
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
RH_EMPRESA_ID=
```

Fallbacks compatibles:

```
IG_PAGE_ID -> META_PAGE_ID
IG_ACCESS_TOKEN -> META_ACCESS_TOKEN
```

## Presets de formulario

Los presets viven en:

```
factory/skills/internos/vertical_meta_ads/meta_lead_form_create/service.py
```

Se seleccionan con `preset`.

Disponibles:

- `reclutamiento_chofer_torton`
- `inmobiliaria_venta_propiedades`

## Destinos de leads

| Destino | Skill |
| --- | --- |
| RH | `vertical_meta_ads/meta_leads_sync_to_rh` |
| Ventas | `vertical_meta_ads/meta_leads_sync_to_sales` |

El preset de chofer torton captura:

- Nombre completo
- Telefono
- Ciudad o zona
- Anios de experiencia manejando torton
- Licencia vigente
- Tipo de licencia
- Disponibilidad para rutas foraneas
- Disponibilidad para iniciar esta semana

El preset inmobiliario captura:

- Nombre completo
- Telefono
- Email
- Tipo de propiedad buscada
- Zona o ciudad de interes
- Presupuesto aproximado
- Forma de compra
- Tiempo estimado de compra
- Credito preaprobado

## Pendiente para produccion

- Webhook realtime de leads.
- Notificacion automatica a Telegram/admin.
- Creativos reales por empresa/campana.
- Landing/politica de privacidad final.
- Activacion controlada despues de revision humana.
