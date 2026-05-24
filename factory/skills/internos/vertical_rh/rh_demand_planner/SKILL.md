# rh_demand_planner

Calcula cuántos operadores hay que contratar y cuántos candidatos poner en pipeline, aplicando tasa de deserción.

## Entradas

| campo | tipo | default | descripción |
|---|---|---|---|
| `puesto` | str | requerido | Nombre del puesto |
| `demanda_total` | int | requerido | Cuántos operadores se necesitan en total |
| `activos_actuales` | int | `0` | Cuántos ya están contratados |
| `zona` | str | `"general"` | Zona geográfica |
| `fecha_objetivo` | str | `""` | Fecha límite (YYYY-MM-DD) |
| `tasa_desercion` | float | `0.20` | % estimado de candidatos que abandonan el proceso |
| `dias_proceso` | int | `14` | Días promedio del proceso de contratación |

## Salida

```json
{
  "ok": true,
  "data": {
    "faltantes": 8,
    "a_contratar": 10,
    "candidatos_a_capturar": 30,
    "nota": "Se necesitan ~30 candidatos en pipeline para cubrir 10 contrataciones."
  }
}
```
