# EMP_CLIENTESVIP
Generado por Factory3 coordinator — solo diseño.

## Objetivo
Porcentajes por cliente/contrato recurrente y descuentos.

## Arquitectura
- Empresa: `EMP_CLIENTESVIP`
- Proyecto: `PROY-001_clientes_vip`
- Vertical: `vertical_clientes_vip`
- Módulo Apps4All: card `clientes_vip`
- Schema: `clientes_vip`
- Auth: Apps4All

## Skill nueva
- `customer_rate_get`

## Contrato skill
- `company_id`, `schema`, `action`, `customer_id`, `service_code`, `qty`, `dry_run`
- Respuesta: `{ok, data: {rate, discount_pct, min_qty, valid_until}}`

## Prompt funcional
"Devuelve tarifa y descuento por cliente/código de servicio."
