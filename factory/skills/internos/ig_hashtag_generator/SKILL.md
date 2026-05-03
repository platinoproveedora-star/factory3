---
name: ig_hashtag_generator
description: Genera sets de hashtags estrategicos para Instagram agrupados por alcance
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

Genera hashtags agrupados en tres niveles de alcance: mass (1M+ posts), mid (100K-1M) y niche (<100K). Los hashtags ya no impulsan discovery pero mejoran el SEO y la categorizacion del contenido.

## Entrada Esperada

- `topic` (str, requerido): tema del post
- `niche` (str, opcional): nicho o industria
- `audience_size` (str, opcional): `"mass"` | `"mid"` | `"niche"`, default `"mid"`
- `count` (int, opcional): total de hashtags 1-50, default 30

## Salida Esperada

- `ok`: booleano
- `data.hashtags.mass`: lista de hashtags de alto alcance
- `data.hashtags.mid`: lista de hashtags de alcance medio
- `data.hashtags.niche`: lista de hashtags de nicho
- `data.total`: total de hashtags generados
- `data.strategy_note`: nota estrategica

## Ejemplo

```python
result = run({"topic": "marketing digital", "niche": "agencias", "count": 30})
# result["data"]["hashtags"]["niche"] -> [...hashtags especificos...]
```

## Variables de entorno

- `ANTHROPIC_API_KEY`: clave de la API de Anthropic (obligatoria)
