# vertical_companies

Vertical de configuracion de empresas. Su responsabilidad es cargar y convertir
la configuracion de `companies/<EMPRESA>` en contexto operativo para agentes y
skills genericos.

No debe publicar campanas ni procesar leads. Eso vive en:

- `vertical_ads` para campanas y guardrails.
- `vertical_meta_ads` para Meta Ads y formularios.
- `vertical_sales` para leads, score, pipeline y follow-up.

## Skills

| Skill | Descripcion |
| --- | --- |
| `vertical_companies/company_config_loader` | Carga `company.config.json` por `company_id` o `config_path`. |
| `vertical_companies/company_context_builder` | Mezcla config de empresa con brief de campana y devuelve contexto normalizado. |
| `vertical_companies/company_dashboard_scaffold` | Crea dashboard Streamlit base con `Campaign Ops` integrado. |

## Flujo

```
company_config_loader
-> company_context_builder
-> vertical_ads/ads_campaign_run
```

## Empresa inicial

La primera empresa configurada es:

```
companies/EMP_CAMP_RSTATE/company.config.json
```
