# Módulo 3: EMP_FACTUFREIGHT
Generado por Factory3 coordinator — solo diseño.

## Objetivo
Facturación electrónica transporte por viaje/cliente.

## Arquitectura
- Empresa: `EMP_FACTUFREIGHT`
- Proyecto: `PROY-001_facturacion_transporte`
- Vertical: `vertical_freight_billing`
- Módulo Apps4All: card `facturacion_transporte`
- Schema: `freight_billing`
- Auth: Apps4All + billing admin

## Skills nuevas
- `freight_invoice_create`
- `freight_invoice_get`
- `freight_invoice_pdf`
- `freight_cancel`

## Contrato skill
- `company_id`, `schema`, `action`, `quote_id`, `invoice_type`, `currency`, `dry_run`
- Respuesta: `{ok, data: {invoice_id, folio, status, xml_link, pdf_link}}`

## Diseño prompt funcional
"Crea factura transporte desde quote_id y devuelve folio y links PDF/XML."

## Reglas
- No CFDI real en dry_run; solo payload.
- Sin lógica inline.

## Checklist cierre
- ] docs creados
- ] skills registradas
- ] dry_run outputs
- ] no código fuera de skills
- ] QA gate pendiente
