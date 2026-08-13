Base template de dashboard Apps4All (Next.js + Vercel).

Incluye, ya funcional y sin identidad de ningun modulo/empresa especifico:

- Auth Apps4All completo: login/logout/me/grants via `lib/auth.ts` + `lib/platform.ts` (JWT, cookies, `platform.access_grants`).
- `lib/factory.ts`: unico punto para llamar skills via Factory API (`POST /run/<skill>`), nunca credenciales Supabase directas en el dashboard.
- `middleware.ts`: protege todas las rutas salvo `/login` y `api/`.
- Paginas base: `/login`, `/dashboard` (home generico), `/settings`.

Identidad del modulo se resuelve en runtime via env, no hardcodeada en el codigo:

- `MODULE_CODE`: usado en login para elegir el grant correcto y filtrar `access_grants`.
- `MODULE_COOKIE_NAME`: nombre de cookie de sesion (opcional, default `apps4all_module_token`).
- `NEXT_PUBLIC_APP_TITLE` / `NEXT_PUBLIC_APP_DESCRIPTION`: titulo/descripcion del dashboard.

`vertical_apps4all_dash/apps4all_dash_scaffold` clona esta carpeta y genera `project.json` + `.env.example` con esas envs ya resueltas para el modulo nuevo. Las paginas de negocio (`/dashboard` real, nuevas rutas) se agregan despues del scaffold — este template solo trae el shell de auth + layout.
