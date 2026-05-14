# vertical_marketing

Vertical para preparar activos de marketing reutilizables antes de pauta:
oferta, copy, angulos, buyer persona, creatividad, compliance, landing y
reporte.

## Skills principales

| Skill | Uso |
| --- | --- |
| `vertical_marketing/marketing_campaign_planner` | Planea campana por objetivo, audiencia, canales, funnel y KPIs. |
| `vertical_marketing/marketing_offer_builder` | Estructura oferta, beneficios, objeciones y CTA. |
| `vertical_marketing/marketing_copy_generator` | Genera variantes de copy para canales. |
| `vertical_marketing/marketing_creative_brief` | Prepara brief para imagen, video, carrusel o anuncio. |
| `vertical_marketing/marketing_angle_generator` | Genera angulos de venta por dolor, deseo, urgencia y prueba social. |
| `vertical_marketing/marketing_persona_builder` | Define buyer persona, objeciones y triggers. |
| `vertical_marketing/marketing_landing_alignment` | Revisa coherencia entre anuncio, oferta, landing y conversion. |
| `vertical_marketing/marketing_compliance_checker` | Revisa claims, promesas sensibles y riesgos de politica. |
| `vertical_marketing/marketing_privacy_notice_builder` | Genera aviso de privacidad base para landings y leads. |
| `vertical_marketing/marketing_mini_landing_scaffold` | Crea mini landing estatica con CTA, ficha y aviso de privacidad. |
| `vertical_marketing/marketing_report_generator` | Genera reporte ejecutivo de resultados y aprendizajes. |

## Flujo recomendado para una mini landing

```text
company_context_builder
-> marketing_offer_builder
-> marketing_copy_generator
-> marketing_privacy_notice_builder
-> marketing_mini_landing_scaffold
-> marketing_landing_alignment
-> ads_campaign_preflight_check
```

## Caso RSTATE

Para `EMP_CAMP_RSTATE`, la mini landing debe tomar datos de:

```text
companies/EMP_CAMP_RSTATE/first_rstate_campaign.json
```

Pendientes antes de publicarla:

- `whatsapp_number`
- `image_url`
- revision legal del aviso de privacidad
- URL publica final de la landing
