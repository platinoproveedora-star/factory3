---
name: meta_refresh_connection
vertical: vertical_meta
kind: executable
entrypoint: skill.py
requires_env: []
---

# meta_refresh_connection

Reconsulta la Page, su Instagram Business Account y, si hay credenciales de app,
el debug del token.

## Input

- `access_token` requerido, o `META_ACCESS_TOKEN` / `IG_ACCESS_TOKEN`.
- `page_id` requerido, o `META_PAGE_ID` / `IG_PAGE_ID`.
- `ig_user_id` opcional.
- `app_id` y `app_secret` opcionales, o `META_APP_ID` / `META_APP_SECRET`.
- `graph_version` opcional. Default `META_GRAPH_API_VERSION`, `IG_GRAPH_API_VERSION` o `v24.0`.
- `dry_run` opcional.

## Output

Devuelve `page`, `instagram_business_account`, `ig_user_id`, `graph_version` y
`token_debug` cuando las credenciales de app estan disponibles.
