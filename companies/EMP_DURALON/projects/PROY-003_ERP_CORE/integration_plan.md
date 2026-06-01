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
- [ ] Crear data skill para dashboard de ventas.
- [ ] Ejecutar SQL en Supabase.
- [ ] Correr `vertical_erp/erp_health_check`.
- [ ] Registrar modulo ventas en `modules.json` como `active` cuando pase health check.

## Fase 3 - Integracion

- [ ] Definir IDs compartidos para clientes, pedidos y centros de costo.
- [ ] Conectar gastos con ventas por `customer_id` y `sales_order_id`.
- [ ] Usar `sales_documents.id` para pedidos enlazados desde gastos.
- [ ] Crear `erp_dashboard_data` para KPIs consolidados.
- [ ] Definir eventos cross-module.

## Fase 4 - Dashboard Central

- [ ] Dashboard ERP central con gastos, ventas, utilidad y CXC.
- [ ] Alertas por gastos altos, CXC vencida y ventas abiertas.
- [ ] Export consolidado.
