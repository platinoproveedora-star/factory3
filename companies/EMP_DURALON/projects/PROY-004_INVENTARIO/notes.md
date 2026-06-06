# Notes - PROY-004

## Decision Principal

El kardex general sera la base inicial del ERP operativo:

- entrada = compra
- salida = remision/venta
- inventario = entradas menos salidas
- lote = texto operativo exacto; debe elegirse/capturarse igual en compras, ventas y ajustes
- costeo = costo por lote + ultimo costo + promedio ponderado

## Productos Clave

- Varilla 3/8
- Varilla 1/2
- Cemento

Regla: alertar diario cuando un cliente tenga 7 dias o mas sin comprar cualquiera de estos productos.

## Costeo

- `lot_unit_cost`: costo real de compra del lote; no se recalcula.
- `last_purchase_cost`: ultimo costo comprado del producto.
- `weighted_avg_cost`: promedio ponderado de existencias actuales por lote.
- Las ventas guardan snapshot de los tres costos para utilidad futura.
- El kardex es la fuente de verdad de inventario y costos.

## Cuidado operativo

- Los lotes son sensibles a escritura exacta. Ejemplo: `12rab21may` y `12RAB21MAY` se comportan como lotes distintos.
- Se agrego skill `erp_inventory_kardex_lot_reassign` para corregir lote de un movimiento ya guardado con auditoria en metadata.
