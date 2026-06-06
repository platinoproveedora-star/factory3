# Notes - PROY-002

## Decisiones

- Usar una tabla unificada `sales_documents` para cotizaciones, pedidos, remisiones y facturas.
- Cada documento conserva `id` y `folio` interno independiente.
- Folios internos usan 5 digitos.
- `external_folio` no aplica para cotizacion; si aplica opcionalmente para pedido, remision y factura.
- `sales_receivables` representa cuentas por cobrar: total, pagado y saldo por cliente/documento.

## No ejecutar todavia

Nota historica: el SQL inicial fue draft. La operacion actual ya usa `uc101_proy002` para remisiones y `uc101_proy004` para clientes/productos/kardex.

## Operacion actual

- La caja de remisiones vive en `proy002-form01_caja_rem`.
- URL publica: `https://uc101-remisiones.onrender.com`.
- Al guardar remision:
  - crea encabezado en `sales_documents`;
  - crea renglones en `sales_document_items`;
  - descuenta inventario con `erp_inventory_kardex_save`;
  - guarda snapshots de costos desde `vertical_erp_costing`.
- No se manejan aun cotizaciones, pedidos, facturas, pagos completos ni SAT.
