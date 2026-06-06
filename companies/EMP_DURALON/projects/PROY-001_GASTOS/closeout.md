# Closeout — PROY-001 — Gastos

**Cerrado:** 2026-06-01
**Estado:** ERP-ready — operativo

## URLs entregadas

| Recurso | URL |
|---|---|
| Dashboard | https://uc101-gastos.onrender.com |
| Bot Telegram | @Duralon1_bot |
| GitHub | https://github.com/platinoproveedora-star/uc101-proy001 |
| Supabase schema | uc101_proy001 (ddcwdtqiupwtyltdpakm) |
| Factory API | https://factory3.onrender.com |

## Entregables completados

- Bot Telegram con 3 modos de captura: manual paso a paso, formato rapido, OCR foto
- Dashboard Next.js con KPIs, tablas por categoria (mes actual y anterior), comparativo mensual, matriz categoria x mes, tabla editable con CRUD completo
- Schema Supabase ERP-ready: 5 tablas con empresa_id/project_code/module_code/folio
- Columna vehiculo para control por unidad
- Campos ERP en gastos para conexion futura con PROY-002 ventas, compras, activos
- CORS habilitado en factory3 para dashboards externos

## ERP Health Check — PASS (2026-06-01)

| Tabla | Estado |
|---|---|
| gastos | OK |
| usuarios | OK |
| categorias_gasto | OK |
| gasto_documentos | OK |
| gasto_eventos | OK |

## Estructura final

```
companies/EMP_DURALON/projects/PROY-001_GASTOS/
  dashboard/gastos/     <- Next.js (repo uc101-proy001, Render)
  project.json
  deliverables.md
  closeout.md

factory/skills/internos/vertical_client_expenses/
  client_expenses_run/
  client_expenses_dashboard_data/

factory/bots/duralon1_bot/bot.py  <- webhook activo
```

## Pendientes post-cierre (no bloqueantes)

- Chat ID de Luis -- se registra en su primer /start
- Confirmar bucket uc101-proy001-assets activo en Supabase Storage

## Conexion ERP

- `PROY-001` queda como modulo de gastos independiente y ERP-ready.
- El ERP completo se documenta en `PROY-003_ERP_CORE`; este proyecto no debe guardar arquitectura global.
- Campos de enlace preparados para crecer: `customer_id`, `supplier_id`, `sales_order_id`, `purchase_order_id`, `cost_center_id`, `asset_id`, `erp_tags`.
- Estado operativo al 2026-06-06: estable; no bloquea PROY-002/003/004.
