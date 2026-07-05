# Apps4All Auth Bridge

Vertical para estandarizar auth de apps vendibles Apps4All.

Contrato:
- Login directo del dashboard con cookie propia.
- SSO desde Apps4All con `apps4all_token`.
- `?sso=` acepta token firmado por `PLATFORM_JWT_SECRET`.
- Todas las apps leen `platform.users`, `platform.companies` y `platform.access_grants`.
- Cada app valida `module_code`.
- Sin company/schema/url hardcodeados en codigo reusable.

Skills:
- `vertical_apps4all_auth_bridge/apps4all_auth_bridge_plan`
- `vertical_apps4all_auth_bridge/apps4all_auth_bridge_health_check`
- `vertical_apps4all_auth_bridge/apps4all_auth_bridge_scaffold`
