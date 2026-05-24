# new_supabase_table

Crea una tabla en Supabase via Management API.

## Context

| Campo | Tipo | Requerido | Descripcion |
|-------|------|-----------|-------------|
| `table_name` | string | si | Nombre de la tabla (snake_case) |
| `columns` | list | si | Lista de columnas |
| `dry_run` | bool | no | Default true — solo muestra el SQL |

### Columna

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `name` | string | Nombre de la columna |
| `type` | string | Tipo SQL: text, integer, numeric, boolean, date, timestamptz, uuid, jsonb |
| `nullable` | bool | Default true |
| `default` | string | Valor por defecto |
| `primary_key` | bool | Clave primaria |
| `unique` | bool | Unique constraint |

## Notas

- Agrega `id uuid primary key default gen_random_uuid()` automaticamente si no esta definido
- Agrega `created_at timestamptz default now()` automaticamente
- Requiere `SUPABASE_ACCESS_TOKEN` y `SUPABASE_URL` en variables de entorno
- Tambien acepta `SUPABASE_PROJECT_REF`; si no existe, lo deriva desde `SUPABASE_URL`
- `dry_run: true` retorna el SQL sin ejecutar

## Ejemplo

```json
{
  "table_name": "factory",
  "columns": [
    {"name": "chat_id", "type": "text", "nullable": false},
    {"name": "concepto", "type": "text"},
    {"name": "monto", "type": "numeric"},
    {"name": "fecha", "type": "date"}
  ],
  "dry_run": false
}
```
