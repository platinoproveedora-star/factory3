# Módulo 4: EMP_FLOTA360
Generado por Factory3 coordinator — solo diseño.

## Objetivo
Control básico de flota vehicular pequeña/mediana.

## Arquitectura
- Empresa: `EMP_FLOTA360`
- Proyecto: `PROY-001_flota_control`
- Vertical: `vertical_fleet_control`
- Módulo Apps4All: card `flota_control`
- Schema: `fleet_control`
- Auth: Apps4All + fleet admin

## Skills nuevas
- `fleet_vehicle_create`
- `fleet_vehicle_list`
- `fleet_maintenance_register`
- `fleet_summary`

## Contrato skill
- `company_id`, `schema`, `action`, `plate`, `brand`, `model`, `year`, `status`, `dry_run`
- Respuesta vehicle list: `{ok, data: {count, items}}`
- Respuesta maintenance: `{ok, data: {vehicle_id, maintenance_id, date, type, cost}}`
- Respuesta summary: `{ok, data: {vehicles, maintenance_open, cost_month}}`

## Diseño prompt funcional
"Lista vehículos por empresa, registra mantenimiento y devuelve resumen abierto/costo."

## Reglas
- Sin lógica inline.
- dry_run=true default.
- Sin datos hardcodeados.

## Checklist cierre
- ] docs creados
- ] skills registradas
- ] dry_run outputs
- ] no código fuera de skills
- ] QA gate pendiente
