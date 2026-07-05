# GPTAds4All - Architecture agent notes

GPTAds4All is a Factory3 product company. Its reusable execution logic lives in
`factory/skills/internos/vertical_gptads4all/`.

- Product company: `EMP_GPTADS4ALL`
- Project: `PROY-001`
- Module: `gptads4all`
- Schema: `gptads4all`

Rules:
- Reusable code must receive `empresa_id`, `project_code`, `module_code`, and `schema` through context/config.
- The Ola 1 schema is documented only in `SCHEMA.sql`; do not apply it without human approval.
- AI calls use Anthropic Haiku through `ANTHROPIC_API_KEY`.
- Writes default to `dry_run=True`.
