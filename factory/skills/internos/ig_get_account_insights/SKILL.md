---
name: ig_get_account_insights
vertical: vertical_instagram
kind: executable
entrypoint: skill.py
requires_env: [IG_ACCESS_TOKEN]
---

# ig_get_account_insights

Obtiene metricas de cuenta de Instagram via Meta Graph API.

## Input

- `connection` opcional desde `vertical_meta`, con `access_token` e `ig_user_id`.
- `ig_user_id` opcional si existe `connection.ig_user_id` o `IG_BUSINESS_ACCOUNT_ID`.
- `metrics` opcional. Default: `views`, `reach`, `follower_count`.
- `period` opcional: `day`, `week` o `month`.
- `since` y `until` opcionales.
- `dry_run` opcional.

## Output

Devuelve `ok: true` con `data.metrics` normalizado por nombre de metrica.
