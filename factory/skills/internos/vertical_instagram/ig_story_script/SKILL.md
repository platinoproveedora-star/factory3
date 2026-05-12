---
name: ig_story_script
description: Genera guion de historia de Instagram con frames, stickers interactivos y CTA
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

Genera guiones para Instagram Stories con estructura de frames de 5 segundos. Los stickers interactivos (polls, preguntas) aumentan drasticamente el engagement ratio. Las Stories duran 24h y son ideales para contenido efimero y CTAs directos.

## Entrada Esperada

- `topic` (str, requerido): tema de la historia
- `frame_count` (int, opcional): 3-10 frames, default 5
- `include_poll` (bool, opcional): incluir sticker de encuesta, default True
- `include_question` (bool, opcional): incluir sticker de pregunta, default False
- `cta` (str, opcional): llamada a la accion deseada
- `tone` (str, opcional): tono de comunicacion

## Salida Esperada

- `ok`: booleano
- `data.frames`: lista de `{number, text, sticker, sticker_config, bg_color_suggestion, duration_seconds}`
- `data.swipe_up_cta`: texto del CTA final

## Ejemplo

```python
result = run({"topic": "lanzamiento de producto", "include_poll": True, "cta": "Desliza para ver mas"})
```

## Variables de entorno

- `ANTHROPIC_API_KEY`: clave de la API de Anthropic (obligatoria)
