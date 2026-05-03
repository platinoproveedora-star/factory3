---
name: ig_carousel_builder
description: Genera estructura de copy slide por slide para carruseles de Instagram
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

Genera el copy completo para cada slide de un carrusel de Instagram. Slide 1 es el hook que determina el swipe-through rate. Cada slide entrega una sola idea clara. El ultimo slide tiene CTA.

## Entrada Esperada

- `topic` (str, requerido): tema del carrusel
- `slide_count` (int, opcional): 3-10 slides, default 7
- `objective` (str, opcional): `"educate"` | `"sell"` | `"entertain"` | `"inspire"`, default `"educate"`
- `tone` (str, opcional): tono de comunicacion
- `brand_voice` (str, opcional): descripcion de la voz de marca

## Salida Esperada

- `ok`: booleano
- `data.cover`: `{headline, subheadline}` del slide portada
- `data.slides`: lista de `{number, headline, body, visual_note}`
- `data.last_slide_cta`: CTA del ultimo slide
- `data.caption`: caption para el post

## Ejemplo

```python
result = run({"topic": "como ahorrar en 2025", "slide_count": 7, "objective": "educate"})
```

## Variables de entorno

- `ANTHROPIC_API_KEY`: clave de la API de Anthropic (obligatoria)
