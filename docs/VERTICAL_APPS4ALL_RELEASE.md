# Apps4All Release

Vertical generica para publicar apps Factory3/Apps4All.

Objetivo:
- Convertir un dashboard local en app publicable.
- Sincronizar Vercel project/env/deploy.
- Registrar URL final en Marketplace.
- Dejar checklist de cierre por modulo.

Skills:
- `vertical_apps4all_release/apps4all_release_plan`
- `vertical_apps4all_release/apps4all_deploy_sync`
- `vertical_apps4all_release/apps4all_module_url_activate`

Flujo:
1. `apps4all_release_plan`
2. `apps4all_deploy_sync` con `dry_run=true`
3. Autorizacion humana
4. `apps4all_deploy_sync` con `dry_run=false` y `confirm_release=true`
5. `apps4all_module_url_activate`
6. `factory_module_publish_check`
