# Registries

Este documento define los registros que mantienen ordenada la fabrica.

## Regla General

Si algo nuevo queda operativo, debe registrarse. No basta con crear el archivo o la carpeta.

## Registries Principales

| Registry | Ubicacion | Que registra |
|---|---|---|
| Skills | `factory/skills/registry.json` | Todos los skills internos disponibles para `SkillRunner`. |
| Dashboards | `docs/DASHBOARDS.md` | Dashboards por empresa, deploy, funcion y skills principales. |
| Tablas | `docs/TABLES.md` | Tablas Supabase por schema, uso y campos. |
| Clientes | `companies/<EMPRESA>/clients/registry.json` | Clientes operados por esa empresa. |
| Portafolio | `companies/EMP_FREELANCE_GROWTH/portfolio/projects.json` | Proyectos que sirven para vender/mostrar experiencia. |

## Skill Registry

Cada skill debe tener entrada en `factory/skills/registry.json` con `tipo`, `nombre`, `vertical`, `descripcion`, `path`, `entrypoint` y `version`.

## Dashboard Registry

Actualizar `docs/DASHBOARDS.md` cuando:

- Se crea dashboard nuevo.
- Cambia URL/deploy.
- Cambian skills principales.
- Cambia storage principal.

## Tables Registry

Actualizar `docs/TABLES.md` cuando:

- Se crea schema Supabase nuevo.
- Se crea tabla nueva.
- Cambia un campo importante.
- Una tabla cambia de responsabilidad.

## Clients Registry

Cada empresa que atiende clientes debe tener:

```text
companies/<EMPRESA>/clients/registry.json
```

Debe guardar:

- `next_number`
- `clients[]`
- `client_id`
- `client_name`
- `status`
- `folder`

Los proyectos dentro de clientes deben usar `PROY-###` y los repos/servicios asociados deben usar el formato tecnico `uc###-proy###`.

## Portfolio Registry

`companies/EMP_FREELANCE_GROWTH/portfolio/projects.json` registra proyectos vendibles. No todo cliente va automaticamente al portafolio; primero debe tener valor comercial y evidencias.

## Checklist de Registro

Antes de cerrar una tarea:

- Si cree skill: actualizar `factory/skills/registry.json`.
- Si cree dashboard: actualizar `docs/DASHBOARDS.md`.
- Si cree tabla/schema: actualizar `docs/TABLES.md`.
- Si cree cliente: actualizar `clients/registry.json`.
- Si el proyecto sirve para vender: actualizar `portfolio/projects.json`.
