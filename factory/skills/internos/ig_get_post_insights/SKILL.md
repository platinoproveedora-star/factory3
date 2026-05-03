---
name: ig_get_post_insights
vertical: vertical_instagram
kind: executable
entrypoint: skill.py
requires_env: [IG_ACCESS_TOKEN]
---

# ig_get_post_insights

Obtiene metricas de un post, Reel o media de Instagram via Graph API.

## Input

- `media_id` requerido.
- `connection` opcional desde `vertical_meta`, con `access_token`.
- `metrics` opcional. Default: `views`, `reach`, `likes`, `comments`, `shares`, `saved`.
- `dry_run` opcional.

## Output

Devuelve `ok: true` con `data.metrics` normalizado por nombre de metrica.
