---
name: ig_calendar_generator
description: Genera calendario editorial mensual de Instagram por semana con formatos y objetivos
version: "0.1.0"
type: internal
entrypoint: skill.py
contract: run(context) -> dict
vertical: vertical_instagram
requires_env: [ANTHROPIC_API_KEY]
dependencies: []
mcps: []
---

## Rol

Genera calendarios editoriales mensuales para Instagram balanceando formatos (Reels, carruseles, posts, stories) y objetivos (reach, engagement, sales, DMs) por semana.

## Entrada Esperada

- `month` (int, requerido): mes 1-12
- `year` (int, requerido): año >= 2024
- `niche` (str, requerido): nicho o industria de la cuenta
- `brand_name` (str, opcional): nombre de la marca
- `posts_per_week` (int, opcional): 1-7, default 5
- `formats` (list, opcional): subconjunto de `["reel", "carousel", "post", "story"]`

## Salida Esperada

- `ok`: booleano
- `data.month`, `data.year`, `data.total_posts`
- `data.weeks`: lista de `{week, posts: [{day, format, topic, objective, caption_hint}]}`

## Ejemplo

```python
result = run({"month": 6, "year": 2025, "niche": "fitness", "posts_per_week": 5})
```

## Variables de entorno

- `ANTHROPIC_API_KEY`: clave de la API de Anthropic (obligatoria)
