# connect_supabase

Valida configuracion y conectividad basica de Supabase.

## Context

| Campo | Tipo | Requerido | Descripcion |
|-------|------|-----------|-------------|
| `mode` | string | no | `config`, `rest`, `management` o `full` |
| `dry_run` | bool | no | Default true; no llama APIs remotas |

## Env

- `SUPABASE_URL`
- `SUPABASE_ANON_KEY` o `SUPABASE_SERVICE_ROLE_KEY` para REST
- `SUPABASE_ACCESS_TOKEN` para Management API
- `SUPABASE_PROJECT_REF` opcional; se puede derivar desde `SUPABASE_URL`
