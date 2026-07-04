# EMP_KPI_FLOTA
Generado por Factory3 coordinator — solo diseño.

## Objetivo
KPI por unidad y chofer.

## Arquitectura
- Empresa: `EMP_KPI_FLOTA`
- Proyecto: `PROY-001_kpi_flota`
- Vertical: `vertical_kpi_flota`
- Módulo Apps4All: card `kpi_flota`
- Schema: `kpi_flota`
- Auth: Apps4All

## Skill nueva
- `fleet_kpi_get`

## Contrato skill
- `company_id`, `schema`, `action`, `vehicle_id`, `from`, `to`, `dry_run`
- Respuesta: `{ok, data: {trips, km, cost, on_time, incidents}}`

## Prompt funcional
"Devuelve KPIs por unidad/chofer en rango de fechas."
