# Documentación — factory3

Índice de toda la documentación del proyecto.

## General
- [README](../README.md) — Arquitectura, patrones de código y cómo arrancar

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
