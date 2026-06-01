# PROY-002 - Ventas, documentos comerciales y cobranza

## Objetivo

Crear el modulo de ventas de Duralon sobre el contrato `vertical_erp`, listo para conectarse con gastos y con el futuro ERP Core.

## Alcance MVP

1. Clientes.
2. Productos / conceptos.
3. Documentos comerciales.
4. Items de documentos.
5. Pagos.
6. Cuentas por cobrar.
7. Base de dashboard comercial.

## Flujo documental

```text
cotizacion -> pedido -> remision -> factura
```

Cada documento tiene su propio `id` UUID y `folio` interno:

```text
COT-00001
PED-00001
REM-00001
FAC-00001
```

## Folios externos

Cotizacion usa solo folio interno.

Pedido, remision y factura pueden tener `external_folio` editable por administrador porque Duralon puede manejar su propio formato:

```text
folio = FAC-00001
external_folio = A-15321
```

Regla:

- `cotizacion`: no pedir `external_folio`.
- `pedido`: permitir `external_folio`.
- `remision`: permitir `external_folio`.
- `factura`: permitir `external_folio`.

## Cuentas por cobrar

`sales_receivables` registra lo que un cliente debe a Duralon por un documento comercial, normalmente factura o pedido.

Ejemplo:

```text
FAC-00025 total = 10000
PAG-00010 pago = 4000
CXC-00018 saldo = 6000
```

## Identidad ERP

```text
empresa_id = EMP_DURALON
project_code = PROY-002
module_code = ventas
schema = uc101_proy002
```

## Integracion con gastos

Ventas se conectara con gastos usando:

- `customer_id`
- `sales_order_id`
- `cost_center_id`
- eventos cross-module

