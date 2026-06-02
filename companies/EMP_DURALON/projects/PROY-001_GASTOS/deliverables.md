# Deliverables — PROY-001 — Gastos

`EMP_DURALON` · `UC-101` (legacy) · `module_code: gastos` · Repo: `platinoproveedora-star/uc101-proy001`

**Estado: ERP-READY** — cerrado 2026-06-01

## Checklist final

- [x] Bot @Duralon1_bot corriendo en factory3 (webhook activo)
- [x] Captura manual — forma rápida (cantidad,fecha,concepto) + /nuevo paso a paso
- [x] OCR/AI para fotos de tickets — Haiku Vision, guarda directo con categoría sugerida
- [x] Base de datos — schema `uc101_proy001`, 5 tablas ERP-ready, 12 categorías seed
- [x] Columna `vehiculo` — control de gasto por unidad
- [x] Dashboard Next.js — https://uc101-gastos.onrender.com
- [x] KPIs mes actual, tablas categoría mes actual vs anterior, comparativo mensual, matriz categoría×mes
- [x] Tabla editable inline — editar, agregar y borrar gastos desde dashboard
- [x] Ordenar tabla por cualquier columna
- [x] Export CSV desde dashboard
- [x] ERP health check PASS — empresa_id, project_code, module_code, folio en las 5 tablas
- [x] Columnas ERP en gastos: cost_center_id, customer_id, supplier_id, sales_order_id, purchase_order_id, asset_id, erp_tags
- [x] Usuarios con global_user_id, modules_allowed para identidad global futura
- [x] Tania pre-registrada (USR-002)
- [x] ACH registrado (USR-003)
- [x] CORS activo en factory3 para requests desde dashboards

## Pendientes post-cierre (no bloqueantes)

- [ ] Chat ID de Luis — se registra automático en su primer /start
- [ ] Confirmar bucket `uc101-proy001-assets` activo en Supabase Storage

## URLs entregadas

| Recurso | URL |
|---|---|
| Dashboard | https://uc101-gastos.onrender.com |
| Bot | @Duralon1_bot |
| GitHub | https://github.com/platinoproveedora-star/uc101-proy001 |
| Supabase schema | uc101_proy001 (proyecto ddcwdtqiupwtyltdpakm) |
| Factory API | https://factory3.onrender.com |
