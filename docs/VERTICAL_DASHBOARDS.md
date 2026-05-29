# Vertical Dashboards

## Objetivo
Disenar dashboards desde el negocio antes de escoger tecnologia. Esta vertical produce el contrato `dashboard_plan` que despues consume una vertical de construccion como `vertical_nextjs`.

## Contrato Principal
El output central es `dashboard_plan`, definido en `docs/schemas/dashboard_plan.schema.json`.

Flujo:
1. `dashboard_requirements_analyzer`
2. `dashboard_data_source_mapper`
3. `dashboard_kpi_designer`
4. `dashboard_module_planner`
5. `dashboard_quality_check`
6. `dashboard_update_planner`

## Skills
| Skill | Funcion |
|---|---|
| `vertical_dashboards/dashboard_requirements_analyzer` | Convierte objetivo, audiencia y restricciones en requerimientos estructurados. |
| `vertical_dashboards/dashboard_data_source_mapper` | Mapea tablas, campos, relaciones y fuentes disponibles. |
| `vertical_dashboards/dashboard_kpi_designer` | Propone KPIs, filtros y agrupaciones para el dashboard. |
| `vertical_dashboards/dashboard_module_planner` | Genera el `dashboard_plan` completo con paginas, modulos y componentes. |
| `vertical_dashboards/dashboard_quality_check` | Valida que el plan tenga datos, KPIs, filtros, modulos y acciones utiles. |
| `vertical_dashboards/dashboard_update_planner` | Convierte cambios pedidos por cliente en un plan de actualizacion. |

## Duralon MVP
Para `UC-101 / PROY-001`, el plan base debe leer `uc101_proy001.gastos` y mostrar:
- Total de gastos.
- Numero de movimientos.
- Gasto por categoria.
- Gasto por dia.
- Tabla filtrable.
- Exportacion Excel/CSV.

