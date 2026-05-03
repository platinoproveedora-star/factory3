---
name: meta_get_auth_url
vertical: vertical_meta
kind: executable
entrypoint: skill.py
requires_env: []
---

# meta_get_auth_url

Construye una URL OAuth de Meta para autorizar permisos necesarios de Instagram.

## Input

- `app_id` opcional si existe `META_APP_ID`.
- `redirect_uri` opcional si existe `META_REDIRECT_URI`.
- `graph_api_version` opcional si existe `META_GRAPH_API_VERSION`; default `v24.0`.
- `scopes` opcional. Lista o texto separado por comas/espacios.
- `state` opcional.
- `auth_type` opcional.
- `response_type` opcional; default `code`.
- `dry_run` opcional.

## Output

Devuelve `auth_url`, `graph_api_version`, `app_id`, `redirect_uri` y `scopes`.
