# EMP_CARGATIP
Generado por Factory3 coordinator — solo diseño.

## Objetivo
Catálogo y tipo de carga por SKU/peligro.

## Arquitectura
- Empresa: `EMP_CARGATIP`
- Proyecto: `PROY-001_carga_tipo`
- Vertical: `vertical_carga_tipo`
- Módulo Apps4All: card `carga_tipo`
- Schema: `carga_tipo`
- Auth: Apps4All

## Skill nueva
- `cargo_type_register`

## Contrato skill
- `company_id`, `schema`, `action`, `sku`, `hazard_class`, `handling`, `weight_limit_kg`, `dry_run`
- Respuesta: `{ok, data: {cargo_id, class, handling, limit}}`

## Prompt funcional
"Registra tipo de carga y devuelve class/handling/limit."
