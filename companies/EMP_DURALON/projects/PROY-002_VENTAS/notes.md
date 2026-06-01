# Notes - PROY-002

## Decisiones

- Usar una tabla unificada `sales_documents` para cotizaciones, pedidos, remisiones y facturas.
- Cada documento conserva `id` y `folio` interno independiente.
- Folios internos usan 5 digitos.
- `external_folio` no aplica para cotizacion; si aplica opcionalmente para pedido, remision y factura.
- `sales_receivables` representa cuentas por cobrar: total, pagado y saldo por cliente/documento.

## No ejecutar todavia

El SQL queda como draft para revision. Ejecutarlo despues de confirmar reglas de negocio y nombres definitivos.

