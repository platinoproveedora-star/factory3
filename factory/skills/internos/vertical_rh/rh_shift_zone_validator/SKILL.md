# rh_shift_zone_validator

Valida tres dimensiones logísticas del candidato contra los requisitos de la vacante usando IA:
- **Turno**: ¿puede trabajar el turno requerido?
- **Zona**: ¿vive a distancia razonable del lugar de trabajo?
- **Transporte**: ¿tiene cómo llegar sin depender de terceros?

Devuelve un veredicto unificado con señales de riesgo y recomendación.

## Input

```json
{
  "turno_requerido": "noche",
  "zona_trabajo": "Zona Industrial Mérida Norte",
  "municipio_trabajo": "Mérida",
  "respuestas": [
    {"pregunta": "¿En qué horario puede trabajar?", "respuesta": "Solo mañanas, tengo hijos"},
    {"pregunta": "¿Dónde vive actualmente?", "respuesta": "Kanasín, Yucatán"},
    {"pregunta": "¿Tiene vehículo propio?", "respuesta": "No, me muevo en camión"}
  ],
  "candidato_id": "uuid-opcional",
  "guardar": false
}
```

- `turno_requerido` — turno que exige la vacante: `mañana` | `tarde` | `noche` | `rotativo` | `partido` | `fines_semana`
- `zona_trabajo` / `municipio_trabajo` — donde está el trabajo (al menos uno)
- `respuestas` — lista de `{pregunta, respuesta}` o texto libre; o bien `candidato_id` para cargar desde Supabase
- `guardar` — si `true` y hay `candidato_id`, guarda en tabla `scores`

## Output

```json
{
  "ok": true,
  "data": {
    "apto": false,
    "turno": {
      "apto": false,
      "turno_candidato": "mañana",
      "match": "incompatible",
      "detalle": "Candidato solo disponible en mañanas, vacante requiere turno noche."
    },
    "zona": {
      "apto": true,
      "zona_candidato": "Kanasín, Yucatán",
      "distancia_estimada": "moderado",
      "detalle": "Kanasín colinda con Mérida, distancia estimada 15-20 min."
    },
    "transporte": {
      "riesgo": "medio",
      "medio": "publico",
      "detalle": "Depende de camión público; en turno noche el servicio es limitado."
    },
    "señales": [
      "Turno incompatible con disponibilidad declarada",
      "Transporte público en turno noche es irregular"
    ],
    "recomendacion": "descartar",
    "resumen": "Candidato no apto por incompatibilidad de turno. La zona es viable pero el transporte público agrava el riesgo en noche."
  }
}
```

- `apto` — `true` solo si turno y zona son aptos
- `turno.match` — `exacto` | `parcial` | `incompatible`
- `zona.distancia_estimada` — `cercano` | `moderado` | `lejano` | `no_determinado`
- `transporte.riesgo` — `bajo` | `medio` | `alto`
- `recomendacion` — `contratar` | `revisar` | `descartar`

## Lógica de recomendación

| Condición | Recomendación |
|---|---|
| Turno apto + zona apta + transporte bajo/medio | `contratar` |
| Alguna dimensión parcial o transporte medio | `revisar` |
| Turno incompatible O (zona lejana + transporte alto) | `descartar` |

## Dependencias

- `ANTHROPIC_API_KEY` — modelo `claude-haiku-4-5-20251001`
- `SUPABASE_URL` / `SUPABASE_KEY` — solo si se usa `candidato_id` o `guardar`

## Tablas Supabase

- `respuestas` (lectura) — `candidato_id`, `pregunta`, `respuesta`, `orden`
- `scores` (escritura) — `candidato_id`, `detalle.shift_zone_validator`
