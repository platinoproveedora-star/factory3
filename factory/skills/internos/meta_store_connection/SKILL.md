---
name: meta_store_connection
vertical: vertical_meta
kind: executable
entrypoint: skill.py
requires_env: []
---

# meta_store_connection

Valida y devuelve un payload portable normalizado de conexion Meta. No guarda en
Supabase ni depende de ningun backend.

## Input

- `access_token` requerido, o `META_ACCESS_TOKEN` / `IG_ACCESS_TOKEN`.
- `page_id` requerido, o `META_PAGE_ID` / `IG_PAGE_ID`.
- `ig_user_id` requerido, o `instagram_business_account`, `META_IG_USER_ID` / `IG_BUSINESS_ACCOUNT_ID`.
- `token_expires_at` opcional en ISO-8601.
- `expires_in` opcional en segundos; se convierte a `token_expires_at` si no viene explicito.
- `scopes`, `permissions` o `permisos` opcional como lista o string.
- `graph_version` opcional. Default `META_GRAPH_API_VERSION`, `IG_GRAPH_API_VERSION` o `v24.0`.
- `page_name`, `ig_username`, `account_id`, `workspace_id`, `connection_id` opcionales.
- `dry_run` opcional.

## Output

Devuelve `payload` con `provider`, `access_token`, `token_expires_at`, `page_id`,
`ig_user_id`, `scopes` y `graph_version`, mas campos opcionales presentes.
