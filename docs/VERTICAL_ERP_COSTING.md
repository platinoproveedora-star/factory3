# Vertical ERP Costing

## Objetivo

Definir el contrato generico de costeo para ERPs Factory3. Esta vertical calcula y normaliza los costos que compras, inventario y ventas deben compartir sin duplicar reglas en dashboards.

## Politica Base

- `lot_unit_cost`: costo real unitario recibido en compra o entrada. No se recalcula ni se modifica desde ventas.
- `last_purchase_cost`: ultimo costo unitario comprado para el producto. Se deriva de la ultima entrada de compra.
- `weighted_avg_cost`: costo promedio ponderado del inventario existente por producto y lote.
- En ventas se guarda snapshot de los tres costos para reportes de utilidad.
- El kardex es la fuente operativa de verdad para existencias y costos.

## Skills

| Skill | Funcion |
|---|---|
| `vertical_erp_costing/erp_costing_policy` | Devuelve la politica y nombres canonicos de costos. |
| `vertical_erp_costing/erp_costing_purchase_apply` | Normaliza el costo de compra antes de guardarlo en kardex. |
| `vertical_erp_costing/erp_costing_sale_snapshot` | Calcula costos de venta por producto/lote y valida saldo. |
| `vertical_erp_costing/erp_costing_inventory_valuation` | Valua inventario por producto y lote desde kardex. |
| `vertical_erp_costing/erp_costing_weighted_average_rebuild` | Recalcula promedio ponderado para auditoria o reportes. |

## Regla de Integracion

Compras debe enviar `unit_cost` neto de IVA al kardex. El IVA queda separado en metadata. Ventas debe pedir snapshot de costeo antes de guardar remision y usar ese snapshot en `sales_document_items` y `erp_kardex`.
