# vertical_apps4all_release

Orquesta el cierre generico de apps/dashboards Apps4All:

- `apps4all_release_plan`
- `apps4all_deploy_sync`
- `apps4all_module_url_activate`

Esta vertical reutiliza:
- `vertical_vercel/*` para infraestructura Vercel.
- `vertical_apps4all_marketplace/*` para publicar URL y metadata.
- `vertical_factory_productization/*` para checks de cierre.

Todos los writes usan `dry_run=True` por defecto.
