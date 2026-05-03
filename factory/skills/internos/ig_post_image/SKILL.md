---
name: ig_post_image
vertical: vertical_instagram
kind: executable
entrypoint: skill.py
requires_env: [IG_ACCESS_TOKEN]
---

# ig_post_image

Publica una imagen en Instagram con caption y alt text opcional.

## Input

- `connection` opcional desde `vertical_meta`, con `access_token` e `ig_user_id`.
- `ig_user_id` opcional si existe `connection.ig_user_id` o `IG_BUSINESS_ACCOUNT_ID`.
- `image_url` requerido. Debe ser una URL publica.
- `caption` opcional.
- `alt_text` opcional.
- `dry_run` opcional.

## Output

Devuelve `post_id`, `permalink` y `creation_id`.
