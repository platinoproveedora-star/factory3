# EMP_RUTASEGURA
Generado por Factory3 coordinator — solo diseño.

## Objetivo
Rutas seguras por zona/horario y alertas operativas.

## Arquitectura
- Empresa: `EMP_RUTASEGURA`
- Proyecto: `PROY-001_ruta_segura`
- Vertical: `vertical_ruta_segura`
- Módulo Apps4All: card `ruta_segura`
- Schema: `ruta_segura`
- Auth: Apps4All

## Skill nueva
- `safe_route_suggest`

## Contrato skill
- `company_id`, `schema`, `action`, `origin`, `destination`, `depart_at`, `vehicle_type`, `dry_run`
- Respuesta: `{ok, data: {route_id, risk_score, alternatives, eta}}`

## Prompt funcional
"Sugiere ruta segura por origen/destino/horario y devuelve score y alternativas."
