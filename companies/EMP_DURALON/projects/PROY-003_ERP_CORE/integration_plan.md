# Integration Plan - PROY-003_ERP_CORE

## Fase 1 - Base ERP

- [x] Crear `docs/VERTICAL_ERP.md`.
- [x] Crear `vertical_erp/erp_identity_contract`.
- [x] Crear `vertical_erp/erp_health_check`.
- [x] Confirmar `PROY-001_GASTOS` ERP-ready a nivel Supabase.
- [x] Crear `PROY-003_ERP_CORE` como contenedor movible.

## Fase 2 - Ventas

- [x] Crear `PROY-002_VENTAS`.
- [x] Definir schema `uc101_proy002`.
- [x] Crear draft de tablas ventas con contrato ERP.
- [x] Modelar documentos comerciales: cotizacion -> pedido -> remision -> factura.
- [x] Ejecutar SQL/migraciones base en Supabase.
- [x] Crear skills de ventas/remisiones.
- [x] Crear form de caja/remisiones.
- [x] Conectar remision con kardex de PROY-004.
- [x] Integrar PDF de remision.
- [ ] Correr `vertical_erp/erp_health_check`.
- [ ] Registrar modulo ventas en `modules.json` como `active` final cuando pase health check.

## Fase 2B - Inventario/Kardex Operativo

- [x] Crear `PROY-004_INVENTARIO`.
- [x] Definir schema `uc101_proy004`.
- [x] Crear draft de tablas: productos, parties, kardex, reglas de recurrencia.
- [x] Crear `vertical_erp_inventory` con skills base.
- [x] Ejecutar SQL en Supabase.
- [x] Correr `vertical_erp/erp_health_check`.
- [x] Crear dashboard operativo de kardex.
- [x] Probar entrada compra y salida remision.
- [x] Agregar compras multi-renglon con IVA y lote.
- [x] Agregar costeo por lote/ultimo/promedio ponderado.
- [x] Agregar reasignacion auditada de lote en kardex.

## Fase 3 - Integracion

- [ ] Definir IDs compartidos para clientes, pedidos y centros de costo.
- [ ] Conectar gastos con ventas por `customer_id` y `sales_order_id`.
- [ ] Usar `sales_documents.id` para pedidos enlazados desde gastos.
- [x] Conectar PROY-004 kardex con PROY-002 remisiones.
- [ ] Crear `erp_dashboard_data` para KPIs consolidados.
- [ ] Definir eventos cross-module.

## Fase 4 - Dashboard Central

- [ ] Dashboard ERP central con gastos, ventas, utilidad y CXC.
- [ ] Alertas por gastos altos, CXC vencida y ventas abiertas.
- [ ] Export consolidado.
