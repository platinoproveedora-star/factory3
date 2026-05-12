---
name: ig_reply_dm
vertical: vertical_instagram
kind: executable
entrypoint: skill.py
requires_env: [IG_ACCESS_TOKEN, IG_PAGE_ID]
---

# ig_reply_dm

Envia un mensaje directo via Instagram Messaging API.

## Input

- `recipient_ig_id` requerido.
- `message` requerido, maximo 1000 caracteres.
- `connection` opcional desde `vertical_meta`, con `access_token` y `page_id`.
- `page_id` opcional si existe `connection.page_id`, `IG_PAGE_ID` o `META_PAGE_ID`.
- `dry_run` opcional.

## Output

Devuelve `message_id` y `recipient_id`.
