# Clients Workflow

Este documento define como Factory3 registra, opera y entrega trabajos para clientes.

## Principio

Hay dos casos distintos:

- **Clientes freelance temporales**: viven dentro de la empresa que los opera. Para Freelance Growth:

```text
companies/EMP_FREELANCE_GROWTH/clients/
```

- **Empresas reales/internas con varios modulos**: viven como empresa propia en `companies/EMP_<NOMBRE>/projects/`.

```text
companies/EMP_DURALON/projects/PROY-001_GASTOS/
```

No se recomienda un `clients/` global en la raiz porque mezcla clientes de negocios distintos y rompe la propiedad operativa. Si una cuenta va a tener varios sistemas operativos, crear una empresa dedicada es mas claro que esconderla dentro de `EMP_FREELANCE_GROWTH`.

## Consecutivos

| Codigo | Significado | Ejemplo |
|---|---|---|
| `UC-###` | Upwork Client / cliente freelance | `UC-101` |
| `PROY-###` | Proyecto dentro de un cliente | `PROY-001` |
| `TASK-###` | Tarea operativa opcional | `TASK-001` |
| `EMP_<NOMBRE>` | Empresa real/interna con varios modulos | `EMP_DURALON` |

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

Formato obligatorio para nombres tecnicos:

```text
uc101-proy001
uc102-proy001
uc102-proy002
```

No usar nombres largos de vacante como repo, servicio Render, URL, carpeta tecnica o bucket. El nombre largo vive en `project_name`, `README.md`, `deliverables.md` y piezas de portafolio.

## Nombres Tecnicos

| Elemento | Formato | Ejemplo |
|---|---|---|
| Cliente | `UC-###` | `UC-101` |
| Proyecto | `PROY-###` | `PROY-001` |
| Repo GitHub | `uc###-proy###` | `uc101-proy001` |
| Dashboard Vercel | `uc###-proy###` | `uc101-proy001` |
| URL Vercel | `https://uc###-proy###.vercel.app` | `https://uc101-proy001.vercel.app` |
| Carpeta Factory3 | `clients/UC-###/projects/PROY-###/` | `clients/UC-101/projects/PROY-001/` |

Regla: los sistemas usan codigos cortos; los humanos ven nombres descriptivos dentro de los documentos.

Para empresas internas, usar el identificador de empresa (`EMP_DURALON`) como codigo principal. Si el proyecto nacio como cliente freelance (`UC-101`), conservarlo solo como `legacy_client_id` para no romper bot/schema/repo existentes.

## Deploy Operativo

La division actual de infraestructura es:

- **Render**: solo Factory API central (`factory3`) y servicios backend estrictamente necesarios.
- **Vercel**: dashboards Next.js, landing pages y frontends de cliente.
- **Supabase**: datos operativos, storage y schemas por cliente/proyecto.

No desplegar cada dashboard o prueba como servicio Render. Esto quema pipeline minutes y puede bloquear deploys de Factory API. Si un dashboard necesita UI, el destino default es Vercel. Si necesita backend, debe consumir Factory API por `/data/...` o una API route server-side.

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

Para clientes reales, no basta con disco local de Render. La decision operativa es GitHub primero, Supabase despues.

1. Crear/actualizar archivos del cliente freelance en `companies/EMP_FREELANCE_GROWTH/clients/` o de empresa interna en `companies/EMP_<NOMBRE>/projects/`.
2. Guardarlos en GitHub automaticamente para historial y recuperacion.
3. Usar Supabase para operacion viva: tiempo, estados, alertas, metricas y busqueda.
4. Registrar assets grandes en Storage.
5. Documentar cierre antes de transferir repo.

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
- Confirmar que el dashboard va a Vercel, salvo decision explicita.
- Confirmar que Render solo tenga servicios necesarios para Factory API/backends.
- Revisar y limpiar servicios Render de prueba antes de hacer deploys masivos.

## Pendientes Operativos

- Auditar Render y eliminar/suspender servicios de prueba o dashboards migrados a Vercel.
- Dejar `factory3` como servicio Render principal para Factory API.
- Documentar en `docs/DASHBOARDS.md` si cada dashboard vive en Vercel, Render legado o local.
