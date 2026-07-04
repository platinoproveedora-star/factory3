# EMP_DOCS4ALL
Generado por Factory3 coordinator — solo diseño.

## Objetivo
Documentos por viaje: licencias, seguro, cartas, operador.

## Arquitectura
- Empresa: `EMP_DOCS4ALL`
- Proyecto: `PROY-001_docs4all`
- Vertical: `vertical_docs4all`
- Módulo Apps4All: card `docs4all`
- Schema: `docs4all`
- Auth: Apps4All

## Skill nueva
- `trip_docs_register`

## Contrato skill
- `company_id`, `schema`, `action`, `trip_id`, `doc_type`, `file_ref`, `expires_at`, `verified`, `dry_run`
- Respuesta: `{ok, data: {doc_id, valid, expires_at, alerts}}`

## Prompt funcional
"Registra documento por viaje y devuelve vigencia y alertas."
