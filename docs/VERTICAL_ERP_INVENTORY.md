# Vertical ERP Inventory

## Objetivo

Vertical operativa para inventario ERP. En etapa 1 resuelve lo urgente para Duralon:

- productos
- clientes/proveedores
- kardex general de entradas y salidas
- consecutivos de compras y remisiones
- inventario actual
- pagos simples por movimiento
- alertas de recurrencia de compra por cliente/producto

## Principio

El kardex es la fuente operativa inicial. Una entrada representa una compra. Una salida representa una remision/venta. Cotizaciones, pedidos y facturas pueden conectarse despues, pero no son obligatorios en la etapa 1.

## Tablas Base

| Tabla | Uso |
|---|---|
| `erp_products` | Catalogo de productos |
| `erp_parties` | Clientes y proveedores |
| `erp_kardex` | Movimientos de entrada/salida/ajuste/devolucion |
| `erp_recurrence_rules` | Reglas de alerta por producto |

## Folios

| Tipo | Prefijo | Ejemplo |
|---|---|---|
| Producto | `PROD` | `PROD-00001` |
| Cliente/proveedor | `PTY` | `PTY-00001` |
| Kardex | `KAR` | `KAR-00001` |
| Compra | `COM` | `COM-00001` |
| Remision/venta | `REM` | `REM-00001` |
| Ajuste | `AJU` | `AJU-00001` |
| Devolucion | `DEV` | `DEV-00001` |

## Kardex

Campos esenciales:

```text
movement_type = entrada | salida | ajuste | devolucion
source_type = compra | remision | ajuste | devolucion
product_id
quantity_in
quantity_out
balance_after
customer_id
supplier_id
purchase_folio
remission_folio
payment_status
```

## Recurrencia

Productos clave:

```text
varilla_3_8: alertar diario si lleva 7 dias o mas sin compra
varilla_1_2: alertar diario si lleva 7 dias o mas sin compra
cemento: alertar diario si lleva 7 dias o mas sin compra
```

## Skills

| Skill | Uso |
|---|---|
| `vertical_erp_inventory/erp_inventory_product_store` | Normaliza alta/edicion de productos |
| `vertical_erp_inventory/erp_inventory_party_store` | Normaliza clientes/proveedores |
| `vertical_erp_inventory/erp_inventory_product_save` | Crea productos en Supabase con contrato ERP |
| `vertical_erp_inventory/erp_inventory_party_save` | Crea/actualiza clientes y proveedores en Supabase |
| `vertical_erp_inventory/erp_inventory_document_folio` | Genera folios de 5 digitos |
| `vertical_erp_inventory/erp_inventory_kardex_validator` | Valida movimientos antes de guardar |
| `vertical_erp_inventory/erp_inventory_kardex_store` | Normaliza movimientos kardex |
| `vertical_erp_inventory/erp_inventory_kardex_save` | Crea compras, remisiones y ajustes manuales en Supabase |
| `vertical_erp_inventory/erp_inventory_stock_report` | Calcula existencias por producto |
| `vertical_erp_inventory/erp_inventory_balance_rebuild` | Reconstruye saldos desde movimientos |
| `vertical_erp_inventory/erp_inventory_dashboard_data` | Devuelve KPIs, CXC simple, ventas del mes, top inventario y recurrencia |

## Dashboard Operativo

Las escrituras del dashboard deben delegar en skills genericos via Factory API:

```text
POST /data/vertical_erp_inventory/erp_inventory_party_save
POST /data/vertical_erp_inventory/erp_inventory_product_save
POST /data/vertical_erp_inventory/erp_inventory_kardex_save
```

Las API routes del dashboard solo deben adaptar la UI al contrato del skill. La logica de negocio reutilizable vive en `vertical_erp_inventory`.
