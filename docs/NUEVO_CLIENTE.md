# Nuevo Cliente — Guía de Arranque

Este documento es el punto de entrada para cualquier chat nuevo que atienda un cliente de Factory3.
Léelo completo antes de tocar código o crear archivos.

## Documentos base que debes conocer

| Documento | Qué explica |
|---|---|
| `docs/FACTORY_ARCHITECTURE.md` | Estructura general de la fábrica |
| `docs/COMPANIES_STANDARD.md` | Cómo vive cada empresa en `companies/` |
| `docs/CLIENTS_WORKFLOW.md` | Cómo trabajamos clientes: UC-###, PROY-###, entrega, cierre |
| `docs/REGISTRIES.md` | Qué registros mandan y dónde se actualizan |
| `docs/TABLES.md` | Tablas Supabase existentes por schema |
| `factory/skills/registry.json` | Skills disponibles y sus paths |

## Paso 1 — Recibir el brief del cliente

Necesitas como mínimo:
- Nombre del cliente o empresa
- Descripción del proyecto (qué quiere)
- Deadline (fecha de entrega)
- Presupuesto acordado

## Paso 2 — Crear el cliente en la fábrica

```python
runner.run("vertical_upwork_clients/upwork_client_init", {
    "client_name": "Nombre del cliente",
    "company_name": "Empresa del cliente",
    "contact_email": "email@cliente.com",
    "platform": "upwork",
    "source_job_url": "https://upwork.com/jobs/...",
    "notes": "Brief completo aquí",
    "dry_run": False,
})
# Retorna: client_id = UC-101 (o el siguiente consecutivo)
```

## Paso 3 — Crear el proyecto

```python
runner.run("vertical_upwork_clients/upwork_client_project_init", {
    "client_id": "UC-101",
    "project_name": "Nombre corto del proyecto",
    "scope": "Descripción técnica de qué se va a construir",
    "budget": "500",
    "deadline": "2026-06-15",
    "repo_name": "uc101-proy001",
    "dry_run": False,
})
# Retorna: project_id = PROY-001
```

## Paso 4 — Crear repo en GitHub

```python
runner.run("vertical_github/github_create_repo", {
    "name": "uc101-proy001",
    "description": "UC-101 - Nombre del proyecto",
    "private": True,
    "auto_init": True,
    "dry_run": False,
})
```

Formato de nombre de repo: `uc###-proy###` — siempre corto, sin nombre largo de vacante.

## Paso 5 — Arrancar el tiempo

Registrar inicio en `time_log.json` dentro de `projects/PROY-001/`:

```json
{
  "started_at": "2026-05-27T00:00:00Z",
  "deadline": "2026-06-15T00:00:00Z",
  "hour_blocks": [],
  "alerts": {
    "every_hours": 10,
    "enabled": true
  }
}
```

## Estructura resultante

```text
companies/EMP_FREELANCE_GROWTH/clients/
  registry.json
  UC-101/
    client.json
    projects/
      PROY-001/
        project.json
        deliverables.md
        closeout.md
        notes.md
        time_log.json
        assets/
```

## Reglas que no se rompen

- El código del cliente va en su repo GitHub, NO dentro de factory3
- Nunca guardar `.env` o secretos en el repo del cliente
- Antes de transferir repo: correr `github_repo_delivery_check`
- Todo proyecto necesita `deliverables.md` y `closeout.md` antes de cerrar
- Registrar horas en `time_log.json` — no en memoria ni en notas sueltas

## Al cerrar el proyecto

```python
runner.run("vertical_upwork_clients/upwork_client_close", {
    "client_id": "UC-101",
    "notes": "Resumen de lo entregado",
    "dry_run": False,
})
```

Luego transferir repo al cliente:

```python
# Primero verificar que no hay secretos
runner.run("vertical_github/github_repo_delivery_check", {
    "repo": "platinoproveedora-star/uc101-proy001",
})

# Luego transferir (requiere confirm:true)
runner.run("vertical_github/github_repo_transfer", {
    "repo": "platinoproveedora-star/uc101-proy001",
    "new_owner": "github_del_cliente",
    "confirm": True,
    "dry_run": False,
})
```

## Referencia rápida de skills

| Skill | Cuándo usarlo |
|---|---|
| `vertical_upwork_clients/upwork_client_init` | Al ganar un cliente nuevo |
| `vertical_upwork_clients/upwork_client_project_init` | Al iniciar un proyecto dentro del cliente |
| `vertical_upwork_clients/upwork_client_status` | Para ver todos los clientes activos |
| `vertical_upwork_clients/upwork_client_deliverables` | Para regenerar checklist de entrega |
| `vertical_upwork_clients/upwork_client_close` | Al cerrar y documentar entrega |
| `vertical_upwork_clients/upwork_client_orchestrator` | Para crear cliente+proyecto de un solo brief |
| `vertical_github/github_create_repo` | Para crear repo del cliente |
| `vertical_github/github_repo_delivery_check` | Antes de transferir repo |
| `vertical_github/github_repo_transfer` | Para transferir repo al cliente al cerrar |
