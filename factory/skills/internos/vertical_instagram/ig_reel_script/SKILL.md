---
name: ig_reel_script
description: Genera guion completo para Reel con hook optimizado para watch time
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

Genera guiones estructurados para Instagram Reels. El hook en los primeros 1-3 segundos es critico para el watch time, que es la senal #1 del algoritmo de Instagram en 2025.

## Entrada Esperada

- `topic` (str, requerido): tema del reel
- `duration_seconds` (int, opcional): duracion 15-90s, default 30
- `tone` (str, opcional): tono deseado
- `hook_type` (str, opcional): `"question"` | `"statement"` | `"statistic"` | `"story"`, default `"statement"`

## Salida Esperada

- `ok`: booleano
- `data.hook`: texto del hook inicial
- `data.segments`: lista con `{second_start, action, spoken_text}`
- `data.cta`: llamada a la accion final
- `data.caption_suggestion`: caption sugerido para el post
- `data.total_seconds`: duracion total

## Ejemplo

```python
result = run({"topic": "3 errores al emprender", "duration_seconds": 45, "hook_type": "statistic"})
```

## Variables de entorno

- `ANTHROPIC_API_KEY`: clave de la API de Anthropic (obligatoria)
