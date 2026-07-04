# Módulo 2: EMP_CARTAPORTE
Generado por Factory3 coordinator — solo diseño.

## Objetivo
Carta porte electrónica por viaje, cumplimiento fiscal.

## Arquitectura
- Empresa: `EMP_CARTAPORTE`
- Proyecto: `PROY-001_carta_porte`
- Vertical: `vertical_carta_porte`
- Módulo Apps4All: card `carta_porte`
- Schema: `carta_porte`
- Auth: Apps4All + operator chofer/cliente

## Skills nuevas
- `carta_porte_create`
- `carta_porte_get`
- `carta_porte_status`
- `carta_porte_pdf`

## Contrato skill
- `company_id`, `schema`, `action`, `trip`, `vehicle`, `driver`, `cargo`, `origin`, `destination`, `dry_run`
- Respuesta: `{ok, data: {folio, status, payload, filename}}`

## Diseño prompt funcional
"Crea carta porte electrónica con trip, vehicle, driver, cargo, origin, destination y devuelve folio y PDF listo."

## Reglas
- No enviar a producción sin validación CFDI/embarque.
- dry_run=true default.
- Sin lógica inline.

## Checklist cierre
- ] docs creados
- ] skills registradas
- ] dry_run outputs
- ] no código fuera de skills
- ] QA gate pendiente
