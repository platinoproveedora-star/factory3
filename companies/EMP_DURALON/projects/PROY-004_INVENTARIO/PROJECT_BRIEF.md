# PROY-004 - Inventario, kardex y recurrencia comercial

## Objetivo

Crear el modulo operativo urgente de Duralon usando un kardex general como base.

## Alcance Etapa 1

1. Catalogo de productos.
2. Clientes y proveedores.
3. Entradas por compra.
4. Salidas por remision/venta.
5. Inventario actual por producto.
6. Estado de pago simple por movimiento.
7. Alertas de recurrencia de compra.

## Decision

No se implementan cotizaciones, pedidos ni facturas en etapa 1. Se deja la arquitectura preparada para conectarlas despues.

## Analisis Requeridos

- Clientes que deben y cuanto deben.
- Ventas por producto del mes actual.
- Inventario de los 5 productos principales.
- Clientes que no han comprado varilla 3/8 en 7 dias o mas.
- Clientes que no han comprado varilla 1/2 en 7 dias o mas.
- Clientes que no han comprado cemento en 7 dias o mas.
- Ultima compra de esos 3 productos por cliente.

