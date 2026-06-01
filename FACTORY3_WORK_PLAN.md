# FACTORY3 WORK PLAN

Plan visible de trabajo para mantener Factory3 ordenada mientras avanzamos con clientes, empresas internas y portafolio.

## 1. Estado Actual

Factory3 esta en fase de prototipo avanzado / pre-producto operativo.

Ya existen:
- Skills reutilizables por vertical.
- Bots Telegram operativos.
- Empresas en `companies/EMP_*`.
- Dashboards historicos en Streamlit.
- Dashboards nuevos moviendose a Next.js + Vercel.
- Supabase como base operativa.
- Render como Factory API central.
- Vercel como capa de dashboards y frontends.

Riesgo principal: mezclar clientes, empresas, pruebas, dashboards y skills en lugares incorrectos.

## 2. Reglas De Arquitectura

- `factory/skills/` guarda capacidades reutilizables.
- `companies/EMP_*` guarda empresas reales, internas o modulos operativos con varios proyectos.
- `companies/EMP_FREELANCE_GROWTH/` guarda nuestra operacion comercial: perfil, portafolio, vacantes y propuestas.
- Clientes freelance temporales pueden vivir en `companies/EMP_FREELANCE_GROWTH/clients/`.
- Empresas reales con varios modulos deben vivir como `companies/EMP_<NOMBRE>/projects/`.
- Render se usa solo para Factory API central (`factory3`) y backends necesarios.
- Vercel se usa para dashboards nuevos, landing pages y frontends de cliente.
- Supabase guarda datos operativos y schemas por empresa/proyecto.
- GitHub guarda codigo, entregables y version historica.

## 3. Prioridades De Esta Semana

1. Dejar `factory3` estable en Render.
2. Probar `/health` y `/data/vertical_client_expenses/client_expenses_dashboard_data`.
3. Terminar dashboard Duralon en Vercel.
4. Limpiar/suspender servicios Render innecesarios.
5. Ordenar `EMP_DURALON` como empresa interna con `PROY-001_GASTOS`.
6. Definir flujo maestro para crear nueva empresa/proyecto.
7. Definir flujo maestro para dashboard Next.js + Vercel.

## 4. Flujos Maestros A Construir

### Crear Empresa/Proyecto

Objetivo: crear empresa, proyecto, docs base, config y registros sin hacerlo a mano.

Pendiente:
- Skill `company_project_init`.
- Actualizar `factory/config/client_projects.json`.
- Crear `README.md`, `company.json`, `project.json`, `deliverables.md`, `notes.md`, `time_log.json`.

### Crear Schema Supabase

Objetivo: crear schema/tablas por empresa/proyecto con doble ID y registros en docs.

Pendiente:
- Orquestador Supabase por tipo de proyecto.
- Actualizar `docs/TABLES.md`.
- Validar exposed schemas cuando aplique.

### Crear Bot

Objetivo: bot dedicado por empresa/proyecto, con token, routing y contexto.

Pendiente:
- Registro estandar en `factory/bots/registry.json`.
- Skill generico para bot por proyecto.
- QA de webhook/polling.

### Crear Dashboard

Objetivo: pasar de requerimientos a dashboard Next.js.

Pipeline esperado:
`requirements -> data source -> KPIs -> module plan -> quality check -> Next.js scaffold -> Vercel`.

Pendiente:
- Orquestador `dashboard_deploy_flow`.
- Template Next.js base estable.
- QA visual y funcional.

### Deploy

Objetivo: evitar despliegues masivos accidentales.

Regla:
- Render: solo Factory API/backends.
- Vercel: dashboards/frontends.

Pendiente:
- Auditoria de servicios Render.
- Checklist antes de deploy.
- Rollback documentado.

### Cierre Y Portafolio

Objetivo: cada proyecto terminado alimenta el portafolio.

Pendiente:
- Screenshots.
- Video corto.
- Case study.
- Lecciones aprendidas.
- Assets para Upwork/Pioneer.

## 5. Pendientes Tecnicos

- Revisar por que Render sigue mostrando `factory3` como `plan: free` cuando el build plan aparece starter.
- Una vez activo Render, redeployar commit actual.
- Validar Factory API publica con el skill de gastos.
- Revisar 91 gastos en Supabase y confirmar si el registro extra es de prueba del bot.
- Subir dashboard `tmp_dash_next/` al repo `platinoproveedora-star/uc101-proy001`.
- Configurar Vercel con `FACTORY_API_URL=https://factory3.onrender.com`.
- Limpiar `tmp_dash_local/` y `tmp_dash_next/` cuando ya no sean temporales.
- Auditar cambios sueltos no revisados: `CLAUDE.md`, `AGENTS.md`, `companies/EMP_PLATIDREN/`.

## 6. Pendientes Comerciales

- Terminar perfil Upwork.
- Preparar portafolio con LOGPLAT, ESTOIKOLAB, RSTATE, Duralon y Freelance Center.
- Crear demos cortos de bots y dashboards.
- Documentar casos con problema, solucion, stack y resultado.
- Definir paquetes vendibles: bot + dashboard, dashboard solo, automatizacion interna, landing/campana.

## 7. Decisiones Abiertas

- Si `UC-###` se mantiene solo para clientes freelance externos o tambien como alias historico.
- Si cada empresa interna debe tener schema con nombre propio (`duralon_gastos`) o mantener legacy (`uc101_proy001`) hasta migracion.
- Si Factory API se queda en Render o migramos a DigitalOcean/VPS cuando haya mas clientes.
- Si Streamlit queda solo como legacy o se mantiene para prototipos rapidos.
- Si el dashboard de Freelance Center se migra a Next.js.

## 8. Checklist Diario

Antes de empezar:
- Revisar `git status`.
- Identificar cambios ajenos y no tocarlos.
- Revisar este plan.
- Elegir una prioridad principal.

Antes de terminar:
- Validar JSON/Python si se tocaron configs o skills.
- Actualizar docs si cambio arquitectura.
- Commit y push si el trabajo esta completo.
- Escribir siguiente accion clara.

