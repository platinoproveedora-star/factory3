---
name: ig_best_time_selector
description: Calcula los mejores horarios de publicacion en Instagram segun formato y region de audiencia
version: "0.1.0"
type: internal
entrypoint: skill.py
contract: run(context) -> dict
vertical: vertical_instagram
requires_env: []
dependencies: []
mcps: []
---

## Rol

Retorna los horarios optimos de publicacion para Instagram basados en datos de rendimiento 2025. Sin llamada a API externa — logica hardcodeada por formato y region. Las primeras 24-48h de engagement son criticas para el algoritmo.

## Entrada Esperada

- `format` (str, requerido): `"reel"` | `"carousel"` | `"post"` | `"story"`
- `audience_region` (str, opcional): `"latam"` | `"us"` | `"europe"` | `"global"`, default `"latam"`
- `count` (int, opcional): cantidad de slots a retornar 1-7, default 3

## Salida Esperada

- `ok`: booleano
- `data.format`: formato consultado
- `data.audience_region`: region consultada
- `data.best_slots`: lista de `{day, time, rank}`
- `data.note`: nota sobre como usar los horarios

## Ejemplo

```python
result = run({"format": "reel", "audience_region": "latam", "count": 3})
# result["data"]["best_slots"] -> [{"day": "Thursday", "time": "09:00", "rank": 1}, ...]
```

## Variables de entorno

Ninguna. Este skill no requiere variables de entorno.
