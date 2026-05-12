---
name: ig_caption_generator
description: Genera un caption completo para Instagram con hook, cuerpo, emojis y CTA
version: "0.1.0"
type: internal
entrypoint: skill.py
contract: run(context) -> dict
vertical: vertical_instagram
requires_env: [ANTHROPIC_API_KEY]
dependencies: []
mcps: []
---

## Rol

Genera captions listos para publicar en Instagram. Estructura siempre: hook en la primera linea (visible antes del "ver mas"), cuerpo con saltos de linea, emojis integrados de forma natural y CTA al final.

## Entrada Esperada

Un diccionario `context` con:

- `topic` (requerido): tema del post
- `tone` (opcional): tono deseado, default `"profesional y cercano"`
- `brand_voice` (opcional): descripcion de la voz de marca
- `cta` (opcional): llamada a la accion deseada

## Salida Esperada

Un diccionario con:

- `ok`: booleano
- `data.caption`: texto del caption listo para publicar
- `data.character_count`: longitud total en caracteres

## Ejemplo

```python
context = {
    "topic": "nuevo producto de skincare para piel mixta",
    "tone": "empoderador y fresco",
    "brand_voice": "marca millennial, directa, sin tecnicismos",
    "cta": "Link en bio para ver la coleccion completa",
}
result = run(context)
# result["data"]["caption"] -> caption listo
```

## Variables de entorno

- `ANTHROPIC_API_KEY`: clave de la API de Anthropic (obligatoria)
