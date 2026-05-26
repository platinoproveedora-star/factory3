# Vertical Upwork Clients

## Objetivo
Gestionar clientes y proyectos ganados en Upwork/Pioneer/directo con consecutivos `UC-###`, carpetas, entregables, cierre y handoff.

## Estructura

```text
companies/EMP_FREELANCE_GROWTH/clients/
  registry.json
  UC-101/
    client.json
    project.json
    deliverables.md
    closeout.md
```

## Skills

| Skill | Funcion |
|---|---|
| `vertical_upwork_clients/upwork_client_init` | Crea cliente, carpeta `UC-###`, `client.json` y actualiza `registry.json`. |
| `vertical_upwork_clients/upwork_client_project_init` | Crea `project.json`, `deliverables.md` y `closeout.md`. |
| `vertical_upwork_clients/upwork_client_status` | Lista clientes, proyectos y estados. |
| `vertical_upwork_clients/upwork_client_deliverables` | Regenera entregables y notas de handoff. |
| `vertical_upwork_clients/upwork_client_close` | Marca entregado y genera cierre. |
| `vertical_upwork_clients/upwork_client_orchestrator` | Desde brief/vacante ganada crea cliente, proyecto y repo opcional. |

## Skills GitHub Relacionados

| Skill | Funcion |
|---|---|
| `github_create_repo` | Ya existente: crea repo para el cliente. |
| `github_repo_delivery_check` | Revisa repo antes de entrega/transfer. |
| `github_repo_transfer` | Inicia transferencia del repo al owner del cliente. |

## Dashboard
Freelance Center usa la pestana `Clients` para:

1. Pegar brief o subir archivo.
2. Orquestar alta completa.
3. Ver lista de clientes/proyectos.
4. Generar entregables/cierre.
5. Preparar repo transfer cuando aplique.
