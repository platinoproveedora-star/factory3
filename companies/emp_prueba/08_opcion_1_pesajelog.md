# EMP_PESAJELOG
Generado por Factory3 coordinator — solo diseño.

## Objetivo
Pesaje y validación de carga por báscula/API antes del viaje.

## Arquitectura
- Empresa: `EMP_PESAJELOG`
- Proyecto: `PROY-001_pesaje_log`
- Vertical: `vertical_pesaje_log`
- Módulo Apps4All: card `pesaje_log`
- Schema: `pesaje_log`
- Auth: Apps4All

## Skill nueva
- `pesaje_register`

## Contrato skill
- `company_id`, `schema`, `action`, `shipment_id`, `weight_kg`, `tare_kg`, `bascula_ref`, `dry_run`
- Respuesta: `{ok, data: {peso_neto, delta, ref, at}}`

## Prompt funcional
"Registra pesaje y validación de carga y devuelve peso neto y referencia."
