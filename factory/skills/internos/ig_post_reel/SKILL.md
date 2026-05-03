---
name: ig_post_reel
vertical: vertical_instagram
kind: executable
entrypoint: skill.py
requires_env: [IG_ACCESS_TOKEN]
---

# ig_post_reel

Publica un Reel y espera a que Meta termine el procesamiento del video.

## Input

- `connection` opcional desde `vertical_meta`, con `access_token` e `ig_user_id`.
- `ig_user_id` opcional si existe `connection.ig_user_id` o `IG_BUSINESS_ACCOUNT_ID`.
- `video_url` requerido. Debe ser una URL publica.
- `caption` opcional.
- `share_to_feed` opcional, default `true`.
- `max_wait_seconds` opcional, entre 60 y 300.
- `dry_run` opcional.

## Output

Devuelve `post_id`, `permalink`, `creation_id` y `processing_seconds`.
