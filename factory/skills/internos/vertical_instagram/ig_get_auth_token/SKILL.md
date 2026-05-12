---
name: ig_get_auth_token
vertical: vertical_instagram
kind: executable
entrypoint: skill.py
requires_env: []
---

# ig_get_auth_token

Intercambia un token corto de Meta por un token de larga duracion.

## Input

- `short_lived_token` requerido.
- `app_id` requerido.
- `app_secret` requerido.
- `dry_run` opcional.

## Output

Devuelve `access_token`, `token_type`, `expires_in` y `expires_in_days`.

