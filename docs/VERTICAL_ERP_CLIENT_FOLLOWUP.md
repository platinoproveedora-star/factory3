# Vertical ERP Client Followup

Seguimiento operativo de clientes para dashboards ERP vendibles.

## Objetivo

Guardar campos editables por cliente sin mezclar identidad de empresa en codigo:

- `comments`
- `last_call_date`
- `next_followup_date`
- `offer_prices`
- `phone`

## Contrato

Todo skill recibe por `context`:

- `schema`
- `company_id` / `empresa_id`
- `project_code`
- `module_code`

Las escrituras usan `dry_run=True` por default. La UI debe enviar `dry_run=False` solo cuando el usuario confirme una edicion.

## Tabla

`erp_client_followups` vive en el schema del modulo que consume el seguimiento. Para billing, se usa el mismo schema de cobranza.

Toda fila conserva doble ID:

- `id uuid primary key`
- `folio text unique not null`

La unicidad operativa es:

`empresa_id + project_code + module_code + customer_key`
