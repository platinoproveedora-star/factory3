---
name: meta_exchange_code
vertical: vertical_meta
kind: executable
entrypoint: skill.py
requires_env: []
---

# meta_exchange_code

Intercambia un `code` OAuth de Meta por un `access_token`.

## Input

- `code` requerido.
- `app_id` opcional si existe `META_APP_ID`.
- `app_secret` opcional si existe `META_APP_SECRET`.
- `redirect_uri` opcional si existe `META_REDIRECT_URI`.
- `graph_api_version` opcional si existe `META_GRAPH_API_VERSION`; default `v24.0`.
- `dry_run` opcional.

## Output

Devuelve `access_token`, `token_type` y, cuando Meta lo incluya, `expires_in` y `expires_in_days`.
