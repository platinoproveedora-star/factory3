# Logplat Fleet4All

- company_id: `EMP_LOGPLAT`
- project_code: `PROY-001`
- module_code: `fleet4all`
- schema: `fleet4all`
- legacy source: root `EMP_LOGPLAT/` using Supabase schema `logplat`

Rules:
- Do not modify the legacy root app or the legacy `logplat` schema during import.
- Imported Fleet4All rows must use `empresa_id = EMP_LOGPLAT`.
- Run `vertical_fleet4all_migration/logplat_import` with `dry_run=true` first.
- Real writes require `dry_run=false` and `confirm=true`.
