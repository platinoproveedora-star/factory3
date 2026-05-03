---
name: ig_schedule_post
vertical: vertical_instagram
kind: executable
entrypoint: skill.py
requires_env: [IG_ACCESS_TOKEN]
---

# ig_schedule_post

Programa una publicacion de imagen para Instagram.

## Input

- `connection` opcional desde `vertical_meta`, con `access_token` e `ig_user_id`.
- `ig_user_id` opcional si existe `connection.ig_user_id` o `IG_BUSINESS_ACCOUNT_ID`.
- `image_url` requerido. Debe ser una URL publica.
- `scheduled_datetime` requerido en formato ISO 8601, entre 10 minutos y 75 dias en el futuro.
- `caption` opcional.
- `alt_text` opcional.
- `dry_run` opcional.

## Output

Devuelve `post_id`, `creation_id`, `scheduled_unix` y `scheduled_iso`.
