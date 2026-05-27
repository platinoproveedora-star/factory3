# Documentación — factory3

Índice de toda la documentación del proyecto.

## General
- [README](../README.md) — Arquitectura, patrones de código y cómo arrancar
- [FACTORY_ARCHITECTURE.md](FACTORY_ARCHITECTURE.md) — Estructura general de Factory3 y reglas de ubicacion
- [COMPANIES_STANDARD.md](COMPANIES_STANDARD.md) — Estandar para crear y ordenar empresas en `companies/`
- [CLIENTS_WORKFLOW.md](CLIENTS_WORKFLOW.md) — Flujo de clientes, proyectos, entregables, repos y cierre
- [REGISTRIES.md](REGISTRIES.md) — Registries obligatorios: skills, dashboards, tablas, clientes y portafolio

## Seguridad
- [SEGURIDAD.md](SEGURIDAD.md) — Variables de entorno, reglas de git, rotación de credenciales, checklist de deploy y skills para crear una nueva fábrica

## Verticales
- [VERTICAL_RH.md](VERTICAL_RH.md) — Recursos Humanos: skills, tablas Supabase, flujo de candidatos, modo `/rh_1`
- [VERTICAL_IG.md](VERTICAL_IG.md) — Instagram: publicación, insights, comentarios
- [VERTICAL_META.md](VERTICAL_META.md) — Autenticación y conexión con Meta / Facebook
- [VERTICAL_BOT.md](VERTICAL_BOT.md) — Bot multicanal: enrutamiento, cuestionarios, captura de candidatos

## Dashboard (EMP_RH1)

- `EMP_RH1/dashboard/app.py` — Streamlit: 5 páginas (Overview, Vacantes, Candidatos, Pipeline, Seeds)
- `EMP_RH1/dashboard/db.py` — conexión Supabase REST sin dependencias extra
- `EMP_RH1/dashboard/requirements.txt` — streamlit + pandas
- `EMP_RH1/dashboard/render.yaml` — config deploy Render como servicio separado
