# skill_comparator

Compara una carpeta ("caja") de skills contra el registry existente. Detecta duplicados exactos, solapamientos funcionales y skills nuevos, y genera una tabla de acción por skill.

## Entradas

| campo        | tipo   | default    | descripción                                               |
|--------------|--------|------------|-----------------------------------------------------------|
| `box_path`   | str    | requerido  | Ruta a carpeta que contiene subcarpetas de skills         |
| `base_dir`   | str    | `"factory"`| Ruta relativa al directorio factory                       |
| `threshold`  | float  | `0.2`      | Umbral mínimo de similitud Jaccard para marcar solapamiento |

La caja debe tener estructura: `box_path/<nombre_skill>/manifest.json` y/o `SKILL.md`.

## Salida

```json
{
  "ok": true,
  "data": {
    "tabla": [
      {
        "skill_caja": "rh_candidate_search",
        "descripcion_caja": "Busca candidatos en Supabase",
        "vertical_caja": "rh",
        "match_exacto": true,
        "skills_similares": [{ "nombre": "rh_candidate_search", "similitud": 1.0 }],
        "similitud_max": 1.0,
        "accion": "duplicado_exacto"
      }
    ],
    "resumen": {
      "duplicados_exactos": 1,
      "solapamientos": 3,
      "nuevos": 5,
      "total_en_caja": 9,
      "total_en_registry": 138
    }
  }
}
```

## Acciones posibles

| accion            | significado                                                  |
|-------------------|--------------------------------------------------------------|
| `duplicado_exacto`| Mismo nombre ya existe en el registry                       |
| `solapamiento`    | Nombre distinto pero descripción con similitud >= threshold  |
| `nuevo`           | Sin coincidencias — skill genuinamente nuevo                 |
