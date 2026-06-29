# Apps4All Auto Prompt

Objetivo: dejar Apps4All como portal central Vercel, integrar Gastos como modulo operativo, y preparar Conta4All/Multi Shopper/Gastos para venta futura con Stripe sin activar cobro todavia.

Alcance:
- Crear `companies/EMP_APPS4ALL/projects/PROY-001_PORTAL`.
- Auth server-side en Vercel contra `platform.users`.
- JWT nuevo compatible con `company_id`, `modulo_code`, `role`, `grant_id`, `plan_code`, `subscription_status`.
- Portal lista grants activos desde `platform.access_grants`.
- Gastos vive en `/apps/gastos`, lee y escribe el schema definido por `GASTOS_SCHEMA` con API routes server-side.
- Conta4All y Multi Shopper quedan compatibles con claims nuevos y con link de regreso al portal.
- `platform` queda Stripe-ready con `companies`, `company_users`, `billing_accounts` y campos Stripe en grants.

No hacer todavia:
- No activar Stripe checkout.
- No cambiar cobros reales.
- No borrar dashboards existentes.
- No depender de Render para el nuevo portal/Gastos.

Criterios de cierre:
- `npm run build` pasa en Apps4All.
- Builds de Conta4All/Multi Shopper no se rompen por cambios de auth.
- SQL platform aplicado sin errores.
- Portal muestra grants.
- `/apps/gastos` lista gastos, permite crear, editar, borrar y exportar CSV.
- Commit y push realizados.
