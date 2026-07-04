# EMP_COBRANZAFLETE
Generado por Factory3 coordinator — solo diseño.

## Objetivo
Cobranza anticipada/finiquitada por viaje.

## Arquitectura
- Empresa: `EMP_COBRANZAFLETE`
- Proyecto: `PROY-001_cobranza_flete`
- Vertical: `vertical_cobranza_flete`
- Módulo Apps4All: card `cobranza_flete`
- Schema: `cobranza_flete`
- Auth: Apps4All

## Skill nueva
- `freight_payment_register`

## Contrato skill
- `company_id`, `schema`, `action`, `trip_id`, `advance`, `balance`, `method`, `status`, `dry_run`
- Respuesta: `{ok, data: {payment_id, collected, pending, proof_ref}}`

## Prompt funcional
"Registra cobranza anticipada/finiquitada y devuelve saldo y comprobante."
