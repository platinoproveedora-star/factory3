---
name: ig_content_brief
description: Genera brief de contenido para Instagram por objetivo de campana
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

Genera briefs accionables para creadores y agentes. El objetivo determina toda la estrategia: reach (contenido shareable), engagement (interaccion), sales (conversion) o dms (respuesta directa).

## Entrada Esperada

- `objective` (str, requerido): `"reach"` | `"engagement"` | `"sales"` | `"dms"`
- `topic` (str, requerido): tema del contenido
- `target_audience` (str, opcional): descripcion de la audiencia objetivo
- `format` (str, opcional): `"reel"` | `"carousel"` | `"story"` | `"post"`, default `"reel"`
- `brand_voice` (str, opcional): descripcion de la voz de marca

## Salida Esperada

- `ok`: booleano
- `data.brief`: `{objective, format, key_message, hook_suggestion, visual_direction, copy_notes, cta, kpis, do, dont}`

## Ejemplo

```python
result = run({"objective": "dms", "topic": "consultoria gratuita", "format": "reel"})
```

## Variables de entorno

- `ANTHROPIC_API_KEY`: clave de la API de Anthropic (obligatoria)
