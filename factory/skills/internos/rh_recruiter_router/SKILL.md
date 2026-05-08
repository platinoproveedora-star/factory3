# rh_recruiter_router

Asigna un candidato calificado al reclutador disponible según empresa/zona y le envía notificación por Telegram.

## Entradas

| campo | tipo | default | descripción |
|---|---|---|---|
| `candidato_id` | str | requerido | UUID del candidato |
| `empresa_id` | str | `""` | Filtrar reclutador por empresa |
| `zona` | str | `""` | Filtrar reclutador por zona |
| `dry_run` | bool | `false` | No enviar Telegram, solo devolver asignación |
| `base_dir` | str | `"factory"` | Ruta al directorio factory |

## Tabla requerida: `reclutadores`

| campo | tipo | descripción |
|---|---|---|
| `id` | uuid | PK |
| `nombre` | text | Nombre del reclutador |
| `telegram_chat_id` | text | Chat ID de Telegram |
| `empresa_id` | text | Empresa asignada |
| `zona` | text | Zona geográfica |
| `activo` | bool | Si está disponible |

## Salida

```json
{
  "ok": true,
  "data": {
    "reclutador_nombre": "María López",
    "telegram_chat_id": "123456789",
    "mensaje_enviado": "Nuevo candidato calificado...",
    "notificacion": {"ok": true}
  }
}
```
