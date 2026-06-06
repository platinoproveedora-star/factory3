# Data Contracts - PROY-003_ERP_CORE

## Contrato Base

Todo registro operativo expuesto al ERP debe incluir:

| Campo | Uso |
|---|---|
| `id` | UUID interno |
| `folio` | ID visible para humanos |
| `empresa_id` | Empresa propietaria |
| `project_code` | Proyecto/modulo origen |
| `module_code` | Modulo funcional |
| `created_at` | Fecha de creacion |
| `updated_at` | Fecha de actualizacion cuando aplique |

## Gastos

Origen: `PROY-001_GASTOS`  
Schema: `uc101_proy001`

Tablas iniciales:

- `usuarios`
- `categorias_gasto`
- `gastos`
- `gasto_documentos`
- `gasto_eventos`

Campos de enlace preparados en `gastos`:

```text
cost_center_id
customer_id
supplier_id
sales_order_id
purchase_order_id
asset_id
erp_tags
```

## Ventas

Origen: `PROY-002_VENTAS`  
Schema: `uc101_proy002`

Tablas:

- `sales_customers`
- `sales_products`
- `sales_documents`
- `sales_document_items`
- `sales_payments`
- `sales_receivables`
- `sales_events`

### Documentos comerciales

El flujo documental de ventas es:

```text
cotizacion -> pedido -> remision -> factura
```

Todos viven en `sales_documents` y se diferencian por `document_type`.

| Tipo | Folio interno | Folio externo |
|---|---|---|
| `cotizacion` | `COT-00001` | No aplica |
| `pedido` | `PED-00001` | Opcional, editable por admin |
| `remision` | `REM-00001` | Opcional, editable por admin |
| `factura` | `FAC-00001` | Opcional, editable por admin |
 
Campos de trazabilidad documental:

```text
id
folio
external_folio
document_type
parent_document_id
root_document_id
```

`folio` es interno Factory/ERP y no se edita. `external_folio` permite capturar el formato real de Duralon para pedido, remision o factura.

### Cuentas por cobrar

`sales_receivables` registra saldos pendientes por cliente/documento:

```text
CXC-00001
customer_id
document_id
total_amount
paid_amount
balance_amount
status
```

### Integracion ventas - inventario

En la operacion actual, cada remision guarda:

```text
sales_documents.id / folio
sales_document_items.id / folio
inventory_product_id
lot_code
lot_cost_snapshot
avg_cost_snapshot
last_cost_snapshot
```

Cada renglon de remision genera un movimiento `erp_kardex`:

```text
source_type = remision
source_folio = REM-00001
remission_folio = REM-00001
product_id = inventory_product_id
lot_code = lote elegido
quantity_out = cantidad vendida
metadata.remision_item_id
metadata.lot_unit_cost
metadata.weighted_avg_cost
metadata.last_purchase_cost
```

## Integracion Gastos - Ventas

Relaciones previstas:

| Desde | Hacia | Uso |
|---|---|---|
| `gastos.customer_id` | `sales_customers.id` | Gasto asociado a cliente |
| `gastos.sales_order_id` | `sales_documents.id` con `document_type='pedido'` | Gasto asociado a venta/pedido |
| `gastos.cost_center_id` | futuro centro de costo | Gasto administrativo u operativo |

## Reglas

- Los dashboards consumen data skills; no leen Supabase directo.
- Las relaciones entre schemas se documentan aunque no tengan FK fisica entre schemas.
- Los eventos cross-module se deben registrar con payload suficiente para auditoria.

## Inventario / Kardex

Origen: `PROY-004_INVENTARIO`  
Schema: `uc101_proy004`

Tablas:

- `erp_products`
- `erp_parties`
- `erp_kardex`
- `erp_recurrence_rules`

El kardex general resuelve etapa 1:

| Movimiento | Significado |
|---|---|
| `entrada` + `source_type=compra` | Compra / entrada de inventario |
| `salida` + `source_type=remision` | Remision / venta / salida de inventario |
| `ajuste` | Correccion de inventario |
| `devolucion` | Regreso de producto |

Campos de enlace:

```text
customer_id
supplier_id
purchase_folio
remission_folio
quote_folio
order_folio
invoice_folio
```

## Costeo

Origen: `vertical_erp_costing` y kardex `uc101_proy004.erp_kardex`.

| Costo | Regla |
|---|---|
| `lot_unit_cost` | Costo real unitario de compra del lote. |
| `last_purchase_cost` | Ultimo costo unitario comprado del producto. |
| `weighted_avg_cost` | Promedio ponderado de existencias actuales por lote. |

Reglas:

- Compras escriben costo neto de inventario por lote.
- IVA se mantiene separado en metadata y totales comerciales.
- Ventas guardan snapshot de costos para utilidad/reportes.
- El lote es texto exacto; debe normalizarse en UI para evitar duplicados.

Reglas de recurrencia:

```text
varilla_3_8: alerta diaria si >= 7 dias sin compra
varilla_1_2: alerta diaria si >= 7 dias sin compra
cemento: alerta diaria si >= 7 dias sin compra
```
