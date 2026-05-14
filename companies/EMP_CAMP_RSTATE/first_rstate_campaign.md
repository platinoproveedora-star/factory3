# First RSTATE Campaign

## Estado

Brief base recibido. Listo para primer `dry_run` antes de crear cualquier activo
real en Meta.

## Objetivo

Crear la primera campana piloto de EMP_CAMP_RSTATE usando el flujo generico:

```
vertical_companies/company_context_builder
-> vertical_ads/ads_campaign_run
-> vertical_meta_ads/meta_lead_form_create
-> vertical_meta_ads/meta_ads_lead_campaign_flow
-> vertical_meta_ads/meta_leads_sync_to_sales
-> vertical_sales/sales_run
```

## Datos necesarios

| Campo | Estado | Notas |
| --- | --- | --- |
| Tipo de propiedad | Completo | Oficina |
| Operacion | Completo | Venta |
| Ubicacion | Completo | Orion Business Hub, Merida, Yucatan, Mexico |
| Precio o rango | Completo | MXN 1,950,000.00 |
| Beneficios principales | Completo | Piso 8, lista para ocupar, 28 m2, para 2 a 6 personas, opcion con o sin inquilino |
| Perfil de comprador | Completo | Inversionista patrimonial, profesionista, pyme, despacho, consultorio administrativo |
| Fotos/renders/videos | Pendiente | Faltan URLs publicas o archivos |
| Landing o contacto | Pendiente | Falta telefono, WhatsApp, landing o asesor responsable |
| Presupuesto diario | Propuesto | MXN 150 a 200 |
| Duracion de prueba | Propuesto | 7 dias |

## Propiedad base

| Campo | Valor |
| --- | --- |
| Nombre comercial | Oficina en Orion Business Hub |
| Tipo | Oficina |
| Edificio | Orion Business Hub |
| Piso | 8 |
| Ciudad | Merida |
| Estado | Yucatan |
| Pais | Mexico |
| Superficie | 28 m2 |
| Capacidad sugerida | 2 a 6 personas |
| Estado fisico | Completamente lista |
| Precio de venta | MXN 1,950,000.00 |
| Renta actual | MXN 17,000 mensuales |
| Entrega | Con o sin inquilino |
| Uso ideal | Oficina privada, despacho profesional, consultorio administrativo, oficina satelite |

## Enfoque comercial

### Oferta principal

Oficina lista en piso 8 de Orion Business Hub, Merida, con opcion de compra para
uso propio o inversion patrimonial. Puede entregarse con inquilino activo que
actualmente paga MXN 17,000 mensuales.

### Angulos de campana

| Angulo | Mensaje |
| --- | --- |
| Inversion con flujo | Compra una oficina que puede conservar inquilino activo y renta mensual actual. |
| Oficina lista | Espacio en piso 8, 28 m2 completamente listos para operar, ideal para equipos de 2 a 6 personas. |
| Ubicacion corporativa | Presencia profesional en Orion Business Hub, Merida. |
| Flexibilidad | Disponible con o sin inquilino, segun objetivo del comprador. |
| Patrimonio empresarial | Activo inmobiliario para profesionistas, despachos o pymes que quieren dejar de rentar. |

### Audiencias sugeridas

| Audiencia | Perfil |
| --- | --- |
| Inversionistas locales | Personas buscando activos inmobiliarios compactos con renta mensual. |
| Profesionistas independientes | Abogados, contadores, consultores, arquitectos, agentes, asesores financieros. |
| Pymes | Empresas pequenas que necesitan oficina lista para equipo de 2 a 6 personas. |
| Compradores patrimoniales | Personas que buscan propiedad comercial en Merida. |
| Empresas foraneas | Negocios que quieren presencia o punto administrativo en Merida. |

### CTAs

- Solicita informacion
- Agenda una visita
- Recibe ficha de inversion
- Pregunta por la opcion con inquilino
- Conoce la oficina lista

### Preguntas clave para calificar lead

| Pregunta | Motivo |
| --- | --- |
| Buscas la oficina para uso propio o inversion? | Diferenciar comprador usuario vs inversionista. |
| Te interesa con inquilino o libre para ocupar? | Detectar intencion principal. |
| Cual es tu forma de compra? | Contado, credito, evaluar opciones. |
| Cuando te gustaria comprar? | Urgencia. |
| Quieres agendar visita o recibir ficha primero? | Siguiente accion. |

## Payload base

```json
{
  "company_id": "EMP_CAMP_RSTATE",
  "dry_run": true,
  "brief": {
    "objective": "leads",
    "audience": "inversionistas inmobiliarios, profesionistas independientes, pymes y compradores patrimoniales interesados en una oficina lista en Merida",
    "property": {
      "property_type": "Oficina",
      "property_name": "Oficina en Orion Business Hub",
      "building": "Orion Business Hub",
      "floor": 8,
      "location": "Merida, Yucatan, Mexico",
      "size_m2": 28,
      "capacity": "2 a 6 personas",
      "price": 1950000,
      "price_range": "MXN 1,950,000",
      "operation_type": "venta",
      "occupancy_options": "con o sin inquilino",
      "current_rent": 17000,
      "current_rent_period": "mensual",
      "main_benefits": [
        "oficina en piso 8 completamente lista",
        "capacidad para 2 a 6 personas",
        "opcion con inquilino activo",
        "renta actual de MXN 17,000 mensuales",
        "ubicacion corporativa en Orion Business Hub"
      ],
      "contact_owner": "ventas"
    },
    "budget": {
      "daily": 200,
      "total": 1400
    }
  }
}
```

## Payload recomendado para primer dry_run

```json
{
  "company_id": "EMP_CAMP_RSTATE",
  "dry_run": true,
  "execute": false,
  "approver": "pendiente",
  "message": "Oficina lista en piso 8 de Orion Business Hub, Merida. 28 m2 para 2 a 6 personas. Disponible con o sin inquilino activo que actualmente paga MXN 17,000 mensuales. Deja tus datos y recibe la ficha.",
  "title": "Oficina en venta en Merida",
  "description": "Lista para ocupar o conservar como inversion con renta mensual actual.",
  "brief": {
    "objective": "leads",
    "audience": "inversionistas inmobiliarios, profesionistas independientes, pymes y compradores patrimoniales interesados en una oficina lista en Merida",
    "property": {
      "property_type": "Oficina",
      "property_name": "Oficina en Orion Business Hub",
      "building": "Orion Business Hub",
      "floor": 8,
      "location": "Merida, Yucatan, Mexico",
      "size_m2": 28,
      "capacity": "2 a 6 personas",
      "price": 1950000,
      "price_range": "MXN 1,950,000",
      "operation_type": "venta",
      "occupancy_options": "con o sin inquilino",
      "current_rent": 17000,
      "current_rent_period": "mensual",
      "main_benefits": [
        "oficina en piso 8 completamente lista",
        "capacidad para 2 a 6 personas",
        "opcion con inquilino activo",
        "renta actual de MXN 17,000 mensuales",
        "ubicacion corporativa en Orion Business Hub"
      ],
      "contact_owner": "ventas"
    },
    "budget": {
      "daily": 200,
      "total": 1400
    }
  }
}
```

## Copy inicial

### Variante 1 - Inversion

Oficina en venta en piso 8 de Orion Business Hub, Merida. 28 m2 completamente
listos y con opcion de conservar inquilino activo pagando MXN 17,000 mensuales.
Solicita la ficha y revisa si encaja con tu estrategia patrimonial.

### Variante 2 - Uso propio

Deja de adaptar espacios desde cero. Oficina lista de 28 m2 en piso 8 de Orion
Business Hub, ideal para equipos de 2 a 6 personas. Agenda una visita y conoce
la opcion de compra.

### Variante 3 - Flexible

Compra oficina en Merida con flexibilidad: usala para tu empresa o conservala
como inversion con inquilino actual. Precio: MXN 1,950,000. Solicita informacion.

## Pendientes antes de ejecutar real

| Pendiente | Por que importa |
| --- | --- |
| Fotos o renders | Meta Ads necesita creativo real para mayor conversion. |
| Contacto/asesor | Para enrutar leads y follow-up. |
| URL de privacidad | Requerida por Lead Forms. |
| Confirmar datos legales/comerciales | Evitar claims incorrectos sobre renta, ocupacion o entrega. |
| Definir si se menciona rendimiento | Compliance: no prometer retorno garantizado. |

## Dashboard Campaign Ops

Para operar esta campana desde dashboard se diseno una rama generica:

```text
Campaign Ops
  Overview
  Campaign
  Uploads
  Preflight
  Leads
  Results
  Settings
```

### Dashboard en Render

| Campo | Valor |
| --- | --- |
| URL publica | `https://emp-camp-rstate-dashboard.onrender.com` |
| Servicio Render | `emp-camp-rstate-dashboard` |
| Estado verificado | `live` |

## Mini landing

Se agregaron skills genericos en `vertical_marketing` para crear landings
reusables:

| Skill | Uso |
| --- | --- |
| `vertical_marketing/marketing_privacy_notice_builder` | Genera `privacy.html` y `privacy.md`. |
| `vertical_marketing/marketing_mini_landing_scaffold` | Genera `index.html` y `render.yaml` de landing estatica. |

Artefactos creados para esta campana:

```text
companies/EMP_CAMP_RSTATE/landing/index.html
companies/EMP_CAMP_RSTATE/landing/privacy.html
companies/EMP_CAMP_RSTATE/landing/privacy.md
companies/EMP_CAMP_RSTATE/landing/render.yaml
```

Pendientes para publicarla:

- Agregar `whatsapp_number` para activar el boton real.
- Agregar `image_url` o foto principal.
- Revisar aviso de privacidad antes de usarlo como definitivo.

Documentacion:

- `companies/EMP_CAMP_RSTATE/DASHBOARD_BRANCH.md`
- `docs/DASHBOARD_CAMPAIGN_OPS.md`

Plantilla reusable:

```text
factory/dashboard_modules/campaign_ops.py
```

El menu `Uploads` servira para subir fotos/renders y obtener el `image_url` que
hoy bloquea el preflight.

## Checklist de ejecucion

| Paso | Skill | Estado |
| --- | --- | --- |
| Cargar config RSTATE | `vertical_companies/company_config_loader` | Probado en dry_run |
| Construir contexto | `vertical_companies/company_context_builder` | Probado en dry_run |
| Generar plan/payloads | `vertical_ads/ads_campaign_run` | Probado en dry_run |
| Preflight antes de lanzar | `vertical_ads/ads_campaign_preflight_check` | Probado en dry_run |
| Revisar aprobacion | `vertical_ads/ads_approval_queue_create` | Generada en dry_run |
| Crear form Meta | `vertical_meta_ads/meta_lead_form_create` | Pendiente |
| Crear campana pausada | `vertical_meta_ads/meta_ads_lead_campaign_flow` | Pendiente |
| Sincronizar leads a ventas | `vertical_meta_ads/meta_leads_sync_to_sales` | Pendiente |

## Dry run 1 - 2026-05-14

### Resultado

| Campo | Valor |
| --- | --- |
| Skill ejecutado | `vertical_ads/ads_campaign_run` |
| `ok` | `true` |
| Estado | `planned` |
| Escritura/publicacion | No |
| Readiness | `ready=true` |
| Campos faltantes de propiedad | Ninguno |
| Presupuesto diario | MXN 200 |
| Presupuesto total | MXN 1,400 |
| Duracion | 7 dias |
| Estado inicial de campana | `PAUSED` |
| Preset de formulario | `inmobiliaria_venta_propiedades` |
| Nivel de riesgo aprobacion | `medio` |

### Nombre de campana generado

```text
EMP_CAMP_RSTATE real_estate leads - Merida, Yucatan, Mexico
```

### Payload de formulario generado

```json
{
  "preset": "inmobiliaria_venta_propiedades",
  "form_name": "EMP_CAMP_RSTATE real_estate leads - Merida, Yucatan, Mexico",
  "privacy_url": null,
  "dry_run": true
}
```

### Payload de campana generado

```json
{
  "campaign_name": "EMP_CAMP_RSTATE real_estate leads - Merida, Yucatan, Mexico",
  "message": "Oficina lista en piso 8 de Orion Business Hub, Merida. 28 m2 para 2 a 6 personas. Disponible con o sin inquilino activo que actualmente paga MXN 17,000 mensuales. Deja tus datos y recibe la ficha.",
  "title": "Oficina en venta en Merida",
  "description": "Lista para ocupar o conservar como inversion con renta mensual actual.",
  "daily_budget": 200.0,
  "days": 7,
  "status": "PAUSED",
  "targeting": {
    "geo_locations": {
      "countries": ["MX"]
    }
  },
  "image_url": null,
  "link": null,
  "dry_run": true
}
```

### Payload de sync generado

```json
{
  "empresa_id": "EMP_CAMP_RSTATE",
  "form_id": "<FORM_ID>",
  "dry_run": true
}
```

### Pendientes detectados despues del dry run

| Pendiente | Prioridad | Notas |
| --- | --- | --- |
| `privacy_url` | Alta | Requerido para crear el Lead Form real en Meta. |
| `image_url` | Alta | Necesitamos foto/render o asset publico para el anuncio. |
| `link` o contacto | Media | Puede ser landing, WhatsApp o pagina informativa. |
| Responsable/aprobador | Media | El dry run uso `pendiente`. |
| Targeting detallado | Media | Por ahora solo pais `MX`; falta afinar Merida/Yucatan y perfiles. |

## Preflight 1 - 2026-05-14

### Resultado

| Campo | Valor |
| --- | --- |
| Skill ejecutado | `vertical_ads/ads_campaign_preflight_check` |
| `ok` | `true` |
| `ready_to_launch` | `false` |
| Risk score | `74` |
| Risk level | `alto` |
| Checks totales | `21` |
| Checks aprobados | `16` |
| Blockers | `2` |
| Warnings | `3` |

### Blockers

| Codigo | Motivo |
| --- | --- |
| `privacy_url` | Falta URL de privacidad requerida para crear Lead Form real. |
| `creative_image_url` | Falta imagen/render publico para el anuncio. |

### Warnings

| Codigo | Motivo |
| --- | --- |
| `destination_link` | Falta landing, WhatsApp o ficha publica para tracking/conversion. |
| `sensitive_claim_review` | El copy menciona renta/inquilino/inversion; requiere revision humana. |
| `ads_guardrails` | Falta tracking/pixel declarado; revisar antes de optimizar. |

### Acciones recomendadas

1. Agregar `privacy_url` antes de crear el Lead Form real.
2. Agregar `image_url` publica de foto/render del anuncio.
3. Agregar landing, WhatsApp o ficha publica si se usara tracking.

## Notas

- No ejecutar en real hasta tener brief y aprobacion.
- El primer run debe ser `dry_run=true`.
- La campana real debe crearse en `PAUSED`.
