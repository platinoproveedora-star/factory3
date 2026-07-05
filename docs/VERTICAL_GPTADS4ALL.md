# GPTAds4All

GPTAds4All genera campanas publicitarias conversacionales desde una referencia de producto.

Pipeline Ola 1:

`RawBrief -> BriefAnalysis -> ProductRef -> ProductBrief -> IntentSet -> ContextHintSet -> CampaignDraft -> CreativeSet -> ExportArtifact`

Skills:
- `vertical_gptads4all/gptads_brief_analyze`
- `vertical_gptads4all/gptads_product_save`
- `vertical_gptads4all/gptads_product_list`
- `vertical_gptads4all/gptads_brief_save`
- `vertical_gptads4all/gptads_brief_list`
- `vertical_gptads4all/gptads_campaign_history`
- `vertical_gptads4all/gptads_product_brief_build`
- `vertical_gptads4all/gptads_intent_research`
- `vertical_gptads4all/gptads_context_hints_generate`
- `vertical_gptads4all/gptads_campaign_build`
- `vertical_gptads4all/gptads_creative_generate`
- `vertical_gptads4all/gptads_bulk_export`

Contexto requerido para writes:
- `empresa_id` o `company_id`
- `schema` desde `project.json` o contexto
- `project_code`
- `module_code`
- `dry_run=True` por defecto
- `gptads_bulk_export` puede usar `persist_db=False` para generar archivos locales sin escribir en Supabase.

Biblioteca multi-tenant:
- La UI entra desde Apps4All con SSO y carga empresas por grants del usuario.
- El usuario escoge empresa antes de trabajar; ese `company_id` se valida server-side contra sus grants.
- Productos, briefs, analisis, campanas, creativos y exports quedan ligados a `company_id`/`empresa_id`, `project_code`, `module_code` y `schema`.
- Ejemplo: una empresa puede guardar productos publicitarios separados como Varilla, Cemento, Cal o Cafe; cada producto conserva briefs y campanas previas.
- El historial por producto expone angulos usados para evitar repetir enfoque en una segunda campana.

La definicion completa de contratos vive en:
`factory/skills/internos/vertical_gptads4all/CONTRACTS.md`.

La definicion SQL vive en:
`factory/skills/internos/vertical_gptads4all/SCHEMA.sql`.

Roadmap Ola 2:
- `advertiser_audit`
- `adgroup_build`
- `landing_generate`
- `platform_validate`
- `metrics_ingest`
- `experiment_score`
