---
name: ig_top_posts_analyzer
vertical: vertical_instagram
kind: executable
entrypoint: skill.py
requires_env: [IG_ACCESS_TOKEN]
---

# ig_top_posts_analyzer

Lista posts recientes de una cuenta y los ordena por una metrica de rendimiento.

## Input

- `connection` opcional desde `vertical_meta`, con `access_token` e `ig_user_id`.
- `ig_user_id` opcional si existe `connection.ig_user_id` o `IG_BUSINESS_ACCOUNT_ID`.
- `limit` opcional, entre 5 y 50.
- `metric` opcional. Default: `views`.
- `dry_run` opcional.

## Output

Devuelve `top_posts` con `rank`, `media_id`, `permalink`, `timestamp`, `media_type` y `metric_value`.
