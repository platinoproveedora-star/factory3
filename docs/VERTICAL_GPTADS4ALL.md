# GPTAds4All

GPTAds4All genera campanas publicitarias conversacionales desde una referencia de producto.

Pipeline Ola 1:

`ProductRef -> ProductBrief -> IntentSet -> ContextHintSet -> CampaignDraft -> CreativeSet -> ExportArtifact`

Skills:
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
