# GPTAds4All

GPTAds4All turns a product reference into a conversational ad campaign package:

`ProductRef -> ProductBrief -> IntentSet -> ContextHintSet -> CampaignDraft -> CreativeSet -> ExportArtifact`

Ola 1 skills:
- `vertical_gptads4all/gptads_product_brief_build`
- `vertical_gptads4all/gptads_intent_research`
- `vertical_gptads4all/gptads_context_hints_generate`
- `vertical_gptads4all/gptads_campaign_build`
- `vertical_gptads4all/gptads_creative_generate`
- `vertical_gptads4all/gptads_bulk_export`

Contracts live in `CONTRACTS.md`. SQL documentation lives in `SCHEMA.sql`.

Environment:
- `ANTHROPIC_API_KEY` for AI skills
- `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` only when `dry_run=False` writes to DB

Execution:
- Use Factory3 `SkillRunner` or the public `/run/{skill_name}` pattern when available in the deployment.
- Writes default to `dry_run=True`.
- `gptads_bulk_export` supports `dry_run=False` with `persist_db=False` to write local CSV/JSON files without Supabase persistence.

Roadmap Ola 2:
- `advertiser_audit`
- `adgroup_build`
- `landing_generate`
- `platform_validate`
- `metrics_ingest`
- `experiment_score`
