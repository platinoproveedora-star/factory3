---
name: meta_extend_token
vertical: vertical_meta
kind: executable
entrypoint: skill.py
requires_env: []
---

# meta_extend_token

Extiende un token corto de Meta usando `grant_type=fb_exchange_token`.

## Input

- `access_token` requerido. Tambien acepta `short_lived_token`.
- `app_id` opcional si existe `META_APP_ID`.
- `app_secret` opcional si existe `META_APP_SECRET`.
- `graph_api_version` opcional si existe `META_GRAPH_API_VERSION`; default `v24.0`.
- `dry_run` opcional.

## Output

Devuelve `access_token`, `token_type`, `expires_in` y `expires_in_days`.
