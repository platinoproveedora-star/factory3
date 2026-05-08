# rh_dimension_analyzer

Analiza una dimensión específica del perfil de un candidato usando IA. Recibe respuestas de entrevista y devuelve score, nivel, señales y recomendación para esa dimensión.

## Dimensiones disponibles

| dimension   | Qué evalúa                                                              |
|-------------|-------------------------------------------------------------------------|
| `conducta`  | Confiabilidad, actitud, historial de conflictos, riesgo conductual      |
| `fisico`    | Resistencia física, horarios extendidos, condiciones difíciles          |
| `compromiso`| Ausentismo, estabilidad laboral, razones de salida, disponibilidad      |
| `maquinaria`| Conocimiento técnico de maquinaria: marcas, modelos, licencias          |
| `rutas`     | Experiencia por tipo de ruta: urbana, federal, foránea, larga distancia |
| `tecnico`   | Herramientas, certificaciones, resolución de problemas en campo         |

## Input

```json
{
  "dimension": "maquinaria",
  "respuestas": [
    {"pregunta": "¿Qué equipos ha operado?", "respuesta": "Tracto Kenworth T800, 3 años"},
    {"pregunta": "¿Tiene licencia federal?", "respuesta": "Sí, tipo E"}
  ],
  "puesto": "Operador de tracto",
  "candidato_id": "uuid-opcional",
  "contexto_extra": "Empresa requiere experiencia en doble remolque",
  "guardar": false
}
```

- `dimension` — requerido, una de las 6 disponibles
- `respuestas` — lista de `{pregunta, respuesta}` o texto libre; o bien `candidato_id` para cargar desde Supabase
- `puesto` — descripción del puesto, afecta el criterio de evaluación
- `guardar` — si `true` y hay `candidato_id`, guarda el score en tabla `scores`

## Output

```json
{
  "ok": true,
  "data": {
    "dimension": "maquinaria",
    "puesto": "Operador de tracto",
    "score": 8,
    "nivel": "alto",
    "resumen": "Candidato con experiencia sólida en Kenworth T800. Posee licencia federal tipo E.",
    "señales": ["3 años en tracto T800", "licencia tipo E vigente"],
    "recomendacion": "contratar"
  }
}
```

- `score` — 1 a 10
- `nivel` — `bajo` / `medio` / `alto`
- `recomendacion` — `contratar` / `revisar` / `descartar`

## Dependencias

- `ANTHROPIC_API_KEY` — modelo `claude-haiku-4-5-20251001`
- `SUPABASE_URL` / `SUPABASE_KEY` — solo si se usa `candidato_id` o `guardar`

## Tablas Supabase

- `respuestas` (lectura) — `candidato_id`, `pregunta`, `respuesta`, `orden`
- `scores` (escritura) — `candidato_id`, `score_total`, `detalle`
