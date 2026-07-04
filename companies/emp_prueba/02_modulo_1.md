# Módulo 1: EMP_FLETECOST
Generado por Factory3 coordinator — solo diseño.

## Objetivo
Cotizador de fletes para camioneros/fleteros independientes.

## Arquitectura
- Empresa: `EMP_FLETECOST`
- Proyecto: `PROY-001_cotizador_fletes` → un solo proyecto.
- Vertical: `vertical_flete_cost`
- Módulo Apps4All: card `cotizador_fletes`
- Schema: `flete_cost`
- Auth: Apps4All grants multiempresa

## Skills nuevas
- `cotizador_flete_calculate`

## Contrato skill
- `company_id`, `schema`, `action`, `origin`, `destination`, `weight_ton`, `distance_km`, `service_type`, `currency`, `dry_run`
- Respuesta: `{ok, data: {quote_id, base, surcharges, total, currency, created_at}}`

## Diseño prompt funcional
"Calcula cotización de flete origen/destino en km, peso en toneladas, tipo carga, y devuelve total desglosado."

## Reglas
- No hardcodear tarifas fijas.
- dry_run=true default para cambios.
- Sin lógica inline en dashboard.

## Checklist cierre
- ] docs creados
- ] skills registradas
- ] dry_run outputs
- ] no código fuera de skills
- ] QA gate pendiente
