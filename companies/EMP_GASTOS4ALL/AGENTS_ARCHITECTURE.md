# EMP_GASTOS4ALL — Arquitectura

## Qué es
Producto SaaS de control de gastos operativos multi-empresa.
Cada cliente accede con sus propias credenciales y ve solo sus datos.

## Auth
Skill centralizado: `vertical_auth_security/security_user_login`
JWT lleva `company_id` que identifica la empresa del usuario.

## Multi-tenant
Schema único `gastos4all` en Supabase.
Todas las tablas tienen `empresa_id NOT NULL`.
Todas las queries filtran por `empresa_id = session.company_id`.

## Skills de datos
- `vertical_client_expenses/client_expenses_dashboard_data` — lectura (soporta empresa_id filter)
- `vertical_client_expenses/client_expenses_run` — escritura CRUD

## Proyectos
- `GASTOS4ALL_V1/` — dashboard Next.js en Vercel
