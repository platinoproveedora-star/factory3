# Módulo 5: EMP_TRACKLIVE
Generado por Factory3 coordinator — solo diseño.

## Objetivo
Tracking básico GPS con ETA simple.

## Arquitectura
- Empresa: `EMP_TRACKLIVE`
- Proyecto: `PROY-001_tracking_basico`
- Vertical: `vertical_tracking_live`
- Módulo Apps4All: card `tracking_live`
- Schema: `tracking_live`
- Auth: Apps4All + dispatcher

## Skills nuevas
- `tracking_trip_create`
- `tracking_trip_get`
- `tracking_location_update`
- `tracking_eta`

## Contrato skill
- `company_id`, `schema`, `action`, `trip_id`, `latitude`, `longitude`, `eta`, `status`, `dry_run`
- Respuesta: `{ok, data: {trip_id, status, eta, last_location, updated_at}}`

## Diseño prompt funcional
"Actualiza ubicación de trip por GPS y devuelve ETA por viaje."

## Reglas
- No guardar history sin schema propio.
- Sin lógica inline.
- dry_run=true default.

## Checklist cierre
- ] docs creados
- ] skills registradas
- ] dry_run outputs
- ] no código fuera de skills
- ] QA gate pendiente
