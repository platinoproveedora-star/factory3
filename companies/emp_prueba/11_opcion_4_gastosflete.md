# EMP_GASTOSFLETE
Generado por Factory3 coordinator — solo diseño.

## Objetivo
Gastos por viaje: diesel, peaje, casetas y extras.

## Arquitectura
- Empresa: `EMP_GASTOSFLETE`
- Proyecto: `PROY-001_gastos_flete`
- Vertical: `vertical_gastos_flete`
- Módulo Apps4All: card `gastos_flete`
- Schema: `gastos_flete`
- Auth: Apps4All

## Skill nueva
- `trip_expense_register`

## Contrato skill
- `company_id`, `schema`, `action`, `trip_id`, `concept`, `amount`, `currency`, `proof_ref`, `dry_run`
- Respuesta: `{ok, data: {expense_id, trip_total, approved}}`

## Prompt funcional
"Registra gasto de viaje y devuelve total acumulado por trip."
