# EMP_MULTASOK
Generado por Factory3 coordinator — solo diseño.

## Objetivo
Multas y defensa por unidad/operador.

## Arquitectura
- Empresa: `EMP_MULTASOK`
- Proyecto: `PROY-001_multas_ok`
- Vertical: `vertical_multas_ok`
- Módulo Apps4All: card `multas_ok`
- Schema: `multas_ok`
- Auth: Apps4All

## Skill nueva
- `fine_register`

## Contrato skill
- `company_id`, `schema`, `action`, `vehicle_id`, `operator_id`, `amount`, `reason`, `status`, `dry_run`
- Respuesta: `{ok, data: {fine_id, amount, status, defense_ref}}`

## Prompt funcional
"Registra multa y devuelve estado y referencia de defensa."
