# rh_contractor_splitter

Divide candidatos calificados (`estado=apto`) entre empresas contratantes respetando cupos.

## Entradas

| campo | tipo | default | descripción |
|---|---|---|---|
| `vacante_id` | str | `null` | Filtrar por vacante específica |
| `empresa_ids` | list | `[]` | IDs de empresas destino (si vacío, usa los del candidato) |
| `cupos` | dict | `{}` | `{"empresa_id": N}` — límite por empresa |
| `score_minimo` | float | `60.0` | Score mínimo para incluir candidato |
| `estado` | str | `"apto"` | Estado de candidatos a incluir |

## Salida

```json
{
  "ok": true,
  "data": {
    "total_candidatos": 45,
    "asignados": 40,
    "sin_asignar": 5,
    "por_empresa": {
      "empresa_abc": ["uuid1", "uuid2"],
      "empresa_xyz": ["uuid3"]
    }
  }
}
```
