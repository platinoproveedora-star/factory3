# Dashboards Registry

Actualizado: 2026-05-26

Este archivo registra dashboards operativos de Factory3. Cada dashboard debe tener empresa, ubicacion, deploy esperado, datos que consume y verticales/skills principales.

## Dashboards

| Dashboard | Empresa | Ubicacion | Deploy | Funcion | Storage/Datos | Skills principales |
|---|---|---|---|---|---|---|
| RSTATE Campaign Dashboard | EMP_CAMP_RSTATE | `companies/EMP_CAMP_RSTATE/dashboard/app.py` | `emp-camp-rstate-dashboard` | Operar campana inmobiliaria, landing, uploads, preflight y Meta flow | Supabase Storage + campaign config local | `vertical_ads/*`, `vertical_marketing/*`, `vertical_meta_ads/*` |
| Estoiko Lab Agents Dashboard | EMP_ESTOIKOLAB | `companies/EMP_ESTOIKOLAB/dashboard/app.py` | `emp-estoikolab-dashboard` | Ver leads, conversaciones y operacion de agentes chat | Supabase schema `estoikolab` + `public.bot_states` | `vertical_chat_agents/*`, `vertical_sales/*` |
| LOGPLAT Dashboard | LOGPLAT | `EMP_LOGPLAT/dashboard/app.py` | dashboard externo/logplat | Operacion de fletera: viajes, gastos, pagos, CXC y KPIs | Supabase schema `logplat` | `vertical_emp_logplat/*` |
| Freelance Center | EMP_FREELANCE_GROWTH | `companies/EMP_FREELANCE_GROWTH/dashboard/app.py` | `emp-freelance-growth-dashboard` | Operar perfil, portafolio, vacantes, propuestas y checklist freelance | Archivos `portfolio/` + Supabase schema `freelance` | `vertical_freelance_growth/*` |

## Reglas

- Todo dashboard nuevo debe registrarse aqui.
- Si crea tablas nuevas, tambien debe actualizar `docs/TABLES.md`.
- Si usa skills nuevos, debe actualizar `factory/skills/registry.json` y la doc de su vertical.
- Preferir tema claro profesional para evitar texto invisible en componentes Streamlit.
