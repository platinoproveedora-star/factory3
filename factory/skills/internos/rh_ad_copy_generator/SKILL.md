# rh_ad_copy_generator

Genera variantes de copy de anuncio de reclutamiento con tono operativo/industrial usando IA.

## Entradas

| campo | tipo | default | descripción |
|---|---|---|---|
| `puesto` | str | requerido | Nombre del puesto |
| `empresa` | str | `""` | Nombre de la empresa |
| `zona` | str | `""` | Ciudad o zona |
| `salario` | str | `""` | Descripción del salario |
| `requisitos` | list | `[]` | Requisitos del puesto |
| `beneficios` | list | `[]` | Beneficios ofrecidos |
| `tono` | str | `"operativo"` | `operativo` / `motivacional` / `urgente` |
| `canal` | str | `"facebook"` | Canal destino del anuncio |
| `variantes` | int | `2` | Cuántas variantes generar |
| `link_bot` | str | `""` | Link del bot a incluir en el copy |

## Salida

```json
{
  "ok": true,
  "data": {
    "copies": [
      "🚛 SE BUSCA OPERADOR DE TRACTOCAMIÓN...",
      "¡OPORTUNIDAD! Maneja con nosotros..."
    ],
    "canal": "facebook",
    "tono": "operativo"
  }
}
```
