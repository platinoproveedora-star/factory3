# Factory Productization

Vertical para convertir modulos Factory3 en productos vendibles, clonables y demo-ready.

Skills:
- `vertical_factory_productization/factory_demo_seed`
- `vertical_factory_productization/factory_module_publish_check`
- `vertical_factory_productization/factory_module_clone_plan`

Contrato operativo:
- Todo modulo vendible debe tener `project.json`.
- Todo write skill debe respetar `dry_run=True` por defecto.
- Antes de cierre: correr `factory_module_publish_check`.
- Antes de copiar a otra empresa: correr `factory_module_clone_plan`.
- El clon real debe validar replacements de `company_id`, `project_code`, `module_code` y `schema`.
