---
name: meta_connection_check
vertical: vertical_meta
kind: executable
entrypoint: skill.py
requires_env: []
---

# meta_connection_check

Valida una conexion Meta/Instagram por llamadas directas basicas a Graph API.
No importa otros skills.

## Input

- `access_token` requerido, o `META_ACCESS_TOKEN` / `IG_ACCESS_TOKEN`.
- `page_id` requerido, o `META_PAGE_ID` / `IG_PAGE_ID`.
- `ig_user_id` opcional, o `instagram_business_account`, `META_IG_USER_ID` / `IG_BUSINESS_ACCOUNT_ID`.
- `scopes`, `permissions` o `permisos` opcional como lista o string.
- `graph_version` opcional. Default `META_GRAPH_API_VERSION`, `IG_GRAPH_API_VERSION` o `v24.0`.
- `dry_run` opcional.

## Output

Devuelve `checks` para token, page e Instagram Business Account; `scopes`;
`permissions_source`; y `ready_flags` para `publishing`, `insights`, `comments`
y `messages`, cada uno con `ready` y `missing_scopes`.
