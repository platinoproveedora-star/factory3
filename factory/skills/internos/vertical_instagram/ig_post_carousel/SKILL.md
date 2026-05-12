---
name: ig_post_carousel
vertical: vertical_instagram
kind: executable
entrypoint: skill.py
requires_env: [IG_ACCESS_TOKEN]
---

# ig_post_carousel

Publica un carrusel de imagenes en Instagram via Meta Graph API.

## Input

- `connection` opcional desde `vertical_meta`, con `access_token` e `ig_user_id`.
- `ig_user_id` opcional si existe `connection.ig_user_id` o `IG_BUSINESS_ACCOUNT_ID`.
- `media_items` requerido: lista de 2 a 10 objetos `{ "type": "IMAGE", "url": "https://..." }`.
- `caption` opcional.
- `dry_run` opcional.

## Output

Devuelve `post_id`, `permalink`, `carousel_id` y `child_count`.
