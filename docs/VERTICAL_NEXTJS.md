# Vertical Next.js

## Objetivo
Construir dashboards web profesionales en Next.js a partir de un `dashboard_plan` generado por `vertical_dashboards`.

## Principio
Next.js es la capa de producto final para clientes. Streamlit se mantiene como prototipo interno o herramienta rapida.

## Skills
| Skill | Funcion |
|---|---|
| `vertical_nextjs/nextjs_dashboard_scaffold` | Crea estructura base Next.js con layout, rutas, estilos y configuracion. |
| `vertical_nextjs/nextjs_supabase_connector` | Genera helper Supabase y soporte para Factory3 `/data/<skill>`. |
| `vertical_nextjs/nextjs_module_generator` | Genera paginas y modulos desde `dashboard_plan`. |
| `vertical_nextjs/nextjs_chart_builder` | Crea componentes de graficas para KPIs y analisis. |
| `vertical_nextjs/nextjs_table_builder` | Crea tabla filtrable con busqueda y export CSV. |
| `vertical_nextjs/nextjs_export_builder` | Crea utilidades de exportacion CSV/Excel-compatible. |
| `vertical_nextjs/nextjs_auth_setup` | Agrega base de login/control de acceso cuando aplique. |
| `vertical_nextjs/nextjs_module_updater` | Actualiza modulos existentes desde un plan de cambios. |

## Flujo
1. Recibir `dashboard_plan`.
2. Crear scaffold.
3. Agregar conectores.
4. Generar modulos, charts, tablas y exports.
5. Revisar con `dashboard_quality_check`.
6. Entregar a `vertical_vercel` para deploy.

