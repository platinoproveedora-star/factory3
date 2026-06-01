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

Origen previsto: `PROY-002_VENTAS`  
Schema previsto: `uc101_proy002`

Tablas candidatas:

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
