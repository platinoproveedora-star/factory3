# vertical_apps4all_auth_bridge

Capa reusable para dashboards Apps4All con doble entrada:

- SSO desde Apps4All (`apps4all_token` o `?sso=...`)
- login directo propio del modulo
- grants en `platform.access_grants`
- cookie propia por modulo

Skills:
- `vertical_apps4all_auth_bridge/apps4all_auth_bridge_plan`
- `vertical_apps4all_auth_bridge/apps4all_auth_bridge_health_check`
- `vertical_apps4all_auth_bridge/apps4all_auth_bridge_scaffold`

`apps4all_auth_bridge_scaffold` escribe archivos solo con `dry_run=false` y `confirm_scaffold=true`.
