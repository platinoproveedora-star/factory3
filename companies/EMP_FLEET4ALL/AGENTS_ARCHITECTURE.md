# Fleet4All - Architecture agent notes

Fleet4All is a Factory3 product company. Its reusable execution logic lives in
`factory/skills/internos/vertical_fleet4all_{modulo}/`.

- Product company: `EMP_FLEET4ALL`
- Project: `PROY-001`
- Module: `fleet4all`
- Schema: `fleet4all`

Rules:
- Reusable code must receive `empresa_id`, `project_code`, `module_code`, and `schema` through context/config.
- The plan lives in `docs/fleet4all_plan/` (00_REGLAS_GLOBALES, 01_CONTRACTS, 02_SCHEMA, 03_INTEGRADOR, BRIEF_M1-M8); do not apply `02_SCHEMA_FLEET4ALL.sql` without human approval.
- Reference-only (read, never edit): `EMP_LOGPLAT/` and `vertical_emp_logplat/` — logic is cloned into new fleet4all skills, not imported.
- AI calls use Anthropic Haiku through `ANTHROPIC_API_KEY`.
- Writes default to `dry_run=True`.
- Test tenant during development: `empresa_id=EMP_DEMO_FLEET`. Real first tenant (post-smoke-F1, migration pending approval): `EMP_LOGPLAT` (Platino Logistica).
