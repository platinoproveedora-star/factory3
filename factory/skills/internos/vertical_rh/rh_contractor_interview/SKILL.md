# rh_contractor_interview

Genera un cuestionario de entrevista personalizado según el contratista (empresa cliente) que solicita el trabajador. Las preguntas se adaptan al equipo que opera el contratista, su zona, sus requisitos específicos y el canal de comunicación.

## Input

```json
{
  "puesto": "Operador de tracto",
  "contratista": "Transportes del Norte SA",
  "requisitos": ["doble remolque", "licencia tipo E", "carta porte"],
  "equipo": ["Kenworth T800", "International ProStar"],
  "zona": "Yucatán - CDMX",
  "profundidad": "media",
  "canal": "telegram",
  "num_preguntas": 8,
  "vacante_id": "uuid-opcional",
  "guardar": false
}
```

- `puesto` — requerido
- `contratista` — requerido, nombre de la empresa que solicita el trabajador
- `requisitos` — lista de requisitos específicos del contratista
- `equipo` — vehículos o maquinaria que opera el contratista
- `zona` — ruta o región de operación
- `profundidad` — `simple` (filtro rápido) / `media` (default) / `robusto` (situacional detallado)
- `canal` — `telegram` | `whatsapp` | `presencial` — ajusta longitud y formato de preguntas
- `num_preguntas` — número de preguntas a generar (default: 8)
- `guardar` — si `true` y hay `vacante_id`, guarda en tabla `cuestionarios`

## Output

```json
{
  "ok": true,
  "data": {
    "puesto": "Operador de tracto",
    "contratista": "Transportes del Norte SA",
    "canal": "telegram",
    "profundidad": "media",
    "preguntas": [
      {"orden": 1, "pregunta": "¿Ha operado Kenworth T800 con doble remolque?", "dimension": "maquinaria"},
      {"orden": 2, "pregunta": "¿Tiene licencia tipo E vigente?", "dimension": "tecnico"},
      {"orden": 3, "pregunta": "¿Conoce la ruta Mérida-CDMX?", "dimension": "rutas"}
    ]
  }
}
```

## Dependencias

- `ANTHROPIC_API_KEY` — modelo `claude-haiku-4-5-20251001`
- `SUPABASE_URL` / `SUPABASE_KEY` — solo si `guardar=true`

## Tablas Supabase

- `cuestionarios` (escritura) — `vacante_id`, `empresa_id`, `preguntas`, `profundidad`, `canal`
