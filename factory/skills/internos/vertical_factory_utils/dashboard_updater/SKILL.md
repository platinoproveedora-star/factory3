# dashboard_updater

Actualiza un dashboard Streamlit existente usando IA. Lee el `app.py` actual, el registry de skills y las tablas disponibles, y aplica los cambios que se le indican sin romper lo que ya funciona.

## Input

```json
{
  "instruccion": "Agrega secciones para Entrevistas y Reclutadores. En Overview agrega métrica de entrevistas agendadas y tasa de aptos vs candidatos totales.",
  "app_path": "EMP_RH1/dashboard/app.py",
  "incluir_registry": true,
  "incluir_tablas": true,
  "dry_run": false
}
```

- `instruccion` — requerido, qué cambios hacer (puede ser largo y detallado)
- `app_path` — ruta al app.py a actualizar (default: `EMP_RH1/dashboard/app.py`)
- `incluir_registry` — si incluye el registry de skills como contexto para la IA (default: `true`)
- `incluir_tablas` — si incluye el índice de TABLES.md como contexto (default: `true`)
- `dry_run` — si `true`, devuelve el código generado pero no escribe el archivo

## Output

```json
{
  "ok": true,
  "data": {
    "app_path": "EMP_RH1/dashboard/app.py",
    "cambios": [
      "Agregada sección Entrevistas con filtros por estado y reclutador",
      "Agregada sección Reclutadores con tabla de activos",
      "Overview: nueva métrica entrevistas agendadas",
      "Overview: nueva métrica tasa de aptos"
    ],
    "dry_run": false,
    "lineas": 340
  }
}
```

- Con `dry_run=true`, el campo `data.codigo` contiene el `app.py` completo generado

## Instrucciones de ejemplo

```
"Agrega la sección Entrevistas con filtro por estado (agendada/cancelada/realizada) y por reclutador"
"En Overview agrega la tasa de conversión (aptos / total candidatos) y el número de entrevistas agendadas esta semana"
"Agrega sección de Reclutadores mostrando nombre, zona, candidatos asignados y si está activo"
"Reorganiza el sidebar en este orden: Overview, Pipeline, Candidatos, Entrevistas, Vacantes, Reclutadores, Seeds"
```

## Contexto que inyecta automáticamente

1. **Registry completo** agrupado por vertical — la IA sabe qué skills existen
2. **Índice de TABLES.md** — la IA sabe qué tablas y campos hay disponibles

## Modelo usado

`claude-sonnet-4-6` con `max_tokens=8192` — necesita espacio para el código completo

## Dependencias

- `ANTHROPIC_API_KEY`
- `docs/TABLES.md` (si `incluir_tablas=true`)
- `factory/skills/registry.json` (si `incluir_registry=true`)
