# Clients Workflow

Este documento define como Factory3 registra, opera y entrega trabajos para clientes.

## Principio

Los clientes viven dentro de la empresa que los opera. Para Freelance Growth:

```text
companies/EMP_FREELANCE_GROWTH/clients/
```

No se recomienda un `clients/` global en la raiz porque mezcla clientes de negocios distintos y rompe la propiedad operativa.

## Consecutivos

| Codigo | Significado | Ejemplo |
|---|---|---|
| `UC-###` | Upwork Client / cliente freelance | `UC-101` |
| `PROY-###` | Proyecto dentro de un cliente | `PROY-001` |
| `TASK-###` | Tarea operativa opcional | `TASK-001` |

## Estructura Estandar

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
        assets/
        time_log.json
```

La version inicial puede crear archivos directamente en `UC-101/`, pero la estructura objetivo es `projects/PROY-001/` para soportar varios proyectos por cliente.

## Repos GitHub

Formato recomendado:

```text
uc101-proy001
uc102-proy001
uc102-proy002
```

No usar nombres largos de vacante como repo. El nombre largo vive en `project_name`.

## Estados

| Estado | Uso |
|---|---|
| `prospect` | Cliente detectado o en negociacion. |
| `active` | Cliente ganado/en ejecucion. |
| `planned` | Proyecto creado, aun sin iniciar. |
| `in_progress` | Trabajo activo. |
| `review` | Entregado para revision. |
| `delivered` | Entregado al cliente. |
| `closed` | Cerrado y documentado. |

## Entregables

Todo proyecto debe tener:

- `deliverables.md`: checklist vivo de entrega.
- `closeout.md`: cierre, URLs, accesos, transferencias y pendientes.
- `notes.md`: decisiones, contexto y notas de comunicacion.
- `assets/`: screenshots, videos, documentos y evidencias.

## Tiempo

El control de tiempo debe vivir por proyecto:

```text
projects/PROY-001/time_log.json
```

Campos recomendados:

```json
{
  "started_at": "",
  "deadline": "",
  "hour_blocks": [],
  "alerts": {
    "every_hours": 10,
    "enabled": true
  }
}
```

## Persistencia

Para clientes reales, no basta con disco local de Render. Regla:

1. Crear/actualizar archivos de cliente.
2. Guardarlos en GitHub o Supabase.
3. Registrar assets grandes en Storage.
4. Documentar cierre antes de transferir repo.

## Skills Actuales

| Skill | Uso |
|---|---|
| `vertical_upwork_clients/upwork_client_init` | Crea cliente `UC-###`. |
| `vertical_upwork_clients/upwork_client_project_init` | Crea proyecto `PROY-###`. |
| `vertical_upwork_clients/upwork_client_status` | Lista estado de clientes. |
| `vertical_upwork_clients/upwork_client_deliverables` | Regenera entregables. |
| `vertical_upwork_clients/upwork_client_close` | Cierra proyecto. |
| `vertical_upwork_clients/upwork_client_orchestrator` | Crea cliente/proyecto desde brief. |

## Checklist Antes de Cliente Externo

- Confirmar persistencia en GitHub o Supabase.
- Confirmar repo corto `uc###-proy###`.
- Confirmar `deliverables.md` y `closeout.md`.
- Confirmar dashboard `Clients`.
- Confirmar que no se guardan secretos en el repo.
