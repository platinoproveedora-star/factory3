# Dashboards Registry

Actualizado: 2026-06-01

Este archivo registra dashboards operativos de Factory3. Cada dashboard debe tener empresa, ubicacion, deploy esperado, datos que consume y verticales/skills principales.

## Dashboards

| Dashboard | Empresa | Ubicacion | Deploy | Funcion | Storage/Datos | Skills principales |
|---|---|---|---|---|---|---|
| RSTATE Campaign Dashboard | EMP_CAMP_RSTATE | `companies/EMP_CAMP_RSTATE/dashboard/app.py` | `emp-camp-rstate-dashboard` | Operar campana inmobiliaria, landing, uploads, preflight y Meta flow | Supabase Storage + campaign config local | `vertical_ads/*`, `vertical_marketing/*`, `vertical_meta_ads/*` |
| Estoiko Lab Agents Dashboard | EMP_ESTOIKOLAB | `companies/EMP_ESTOIKOLAB/dashboard/app.py` | `emp-estoikolab-dashboard` | Ver leads, conversaciones y operacion de agentes chat | Supabase schema `estoikolab` + `public.bot_states` | `vertical_chat_agents/*`, `vertical_sales/*` |
| LOGPLAT Dashboard | LOGPLAT | `EMP_LOGPLAT/dashboard/app.py` | dashboard externo/logplat | Operacion de fletera: viajes, gastos, pagos, CXC y KPIs | Supabase schema `logplat` | `vertical_emp_logplat/*` |
| Freelance Center | EMP_FREELANCE_GROWTH | `companies/EMP_FREELANCE_GROWTH/dashboard/app.py` | `emp-freelance-growth-dashboard` | Operar perfil, portafolio, vacantes, propuestas y checklist freelance | Archivos `portfolio/` + Supabase schema `freelance` | `vertical_freelance_growth/*` |
| Duralon Gastos | EMP_DURALON | `companies/EMP_DURALON/projects/PROY-001_GASTOS/dashboard/gastos/` + repo `uc101-proy001` | https://uc101-gastos.onrender.com | KPIs, tabla por categoria, comparativo mensual, movimientos con export CSV | Supabase schema `uc101_proy001` via Factory API | `vertical_client_expenses/*` |
| Duralon Inventario | EMP_DURALON | `companies/EMP_DURALON/projects/PROY-004_INVENTARIO/dashboard/inventario/` | Vercel pendiente | Operar productos, proveedores, clientes, compras/entradas, ventas/salidas e inventario | Supabase schema `uc101_proy004` via dashboard API routes | `vertical_erp_inventory/*`, `vertical_supabase/*` |

## Reglas

- Todo dashboard nuevo debe registrarse aqui.
- Si crea tablas nuevas, tambien debe actualizar `docs/TABLES.md`.
- Si usa skills nuevos, debe actualizar `factory/skills/registry.json` y la doc de su vertical.
- Preferir tema claro profesional para evitar texto invisible en componentes Streamlit.
- Dashboards nuevos de cliente deben vivir en Vercel por default.
- Render queda reservado para Factory API central (`factory3`) y backends necesarios.
- Antes de desplegar o probar muchos servicios, auditar Render y limpiar/suspender dashboards o servicios de prueba para no agotar pipeline minutes.

## Pendientes

- Auditar servicios Render existentes y clasificar: mantener, migrar a Vercel, suspender o borrar.
- Actualizar esta tabla indicando si cada dashboard es Vercel, Render legado o local.
