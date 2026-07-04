# EMP_FOTOFLET
Generado por Factory3 coordinator — solo diseño.

## Objetivo
Foto check carga/daño antes y después del viaje.

## Arquitectura
- Empresa: `EMP_FOTOFLET`
- Proyecto: `PROY-001_foto_flet`
- Vertical: `vertical_foto_flet`
- Módulo Apps4All: card `foto_flet`
- Schema: `foto_flet`
- Auth: Apps4All

## Skill nueva
- `photo_evidence_upload`

## Contrato skill
- `company_id`, `schema`, `action`, `trip_id`, `stage`, `content_b64`, `file_type`, `notes`, `dry_run`
- Respuesta: `{ok, data: {photo_id, url, at, verified}}`

## Prompt funcional
"Sube evidencia foto por etapa de viaje y devuelve ref/estado."
