# Apps4All Factory

Vertical maestra para crear o replicar apps Apps4All.

Flujo canonico:
1. Resolver spec de app.
2. Crear/validar empresa y proyecto.
3. Crear/validar auth bridge.
4. Crear/validar dashboard.
5. Crear/validar skills/schema del modulo.
6. Registrar marketplace.
7. Crear demo seed Apps4All.
8. Auditar hardcodes.
9. Planear billing Stripe.
10. Build/smoke.
11. Release Vercel y activar URL.
12. Monitoreo operativo.

Skills:
- `vertical_apps4all_factory/apps4all_company_project_scaffold`
- `vertical_apps4all_factory/apps4all_factory_build_plan`
- `vertical_apps4all_factory/apps4all_factory_build_orchestrator`
- `vertical_apps4all_productization/apps4all_demo_seed`
- `vertical_apps4all_productization/apps4all_publish_check`
- `vertical_apps4all_billing_stripe/apps4all_billing_plan`
- `vertical_apps4all_remote_smoke_suite/apps4all_remote_smoke_plan`
- `vertical_apps4all_ops_monitoring/apps4all_ops_monitoring_plan`

Todo write real debe pasar por `dry_run=false` y confirmaciones explicitas de las verticales invocadas.
