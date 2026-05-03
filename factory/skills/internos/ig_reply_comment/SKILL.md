---
name: ig_reply_comment
vertical: vertical_instagram
kind: executable
entrypoint: skill.py
requires_env: [IG_ACCESS_TOKEN]
---

# ig_reply_comment

Responde a un comentario de Instagram via Graph API.

## Input

- `comment_id` requerido.
- `connection` opcional desde `vertical_meta`, con `access_token`.
- `message` requerido, maximo 2200 caracteres.
- `dry_run` opcional.

## Output

Devuelve `reply_id` y `comment_id`.
