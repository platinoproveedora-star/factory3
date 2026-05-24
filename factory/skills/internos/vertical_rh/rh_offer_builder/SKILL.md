# rh_offer_builder

Construye la oferta laboral completa con IA. Si no hay `ANTHROPIC_API_KEY`, genera texto de fallback estructurado.

## Entradas

| campo | tipo | default | descripción |
|---|---|---|---|
| `puesto` | str | requerido | Nombre del puesto |
| `empresa` | str | `""` | Nombre de la empresa |
| `zona` | str | `""` | Ciudad o zona |
| `salario_min` | int | `null` | Salario mínimo MXN |
| `salario_max` | int | `null` | Salario máximo MXN |
| `tipo_contrato` | str | `"indefinido"` | indefinido / temporal / por proyecto |
| `beneficios` | list | `[]` | Lista de beneficios |
| `requisitos` | list | `[]` | Lista de requisitos |
| `notas_extra` | str | `""` | Contexto adicional para la IA |

## Salida

```json
{
  "ok": true,
  "data": {
    "puesto": "Operador de Tractocamión",
    "salario": "$18,000 - $22,000 MXN",
    "texto_oferta": "SE BUSCA OPERADOR DE TRACTOCAMIÓN...",
    "generado_con_ia": true
  }
}
```
