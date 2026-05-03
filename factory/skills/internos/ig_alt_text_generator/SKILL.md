---
name: ig_alt_text_generator
description: Genera alt text descriptivo para imagenes de Instagram para accesibilidad y SEO
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

Genera alt text para el campo de accesibilidad de Instagram (disponible en Graph API desde marzo 2025). Mejora la accesibilidad para lectores de pantalla y el SEO de la cuenta. Maximo 125 caracteres, sin comenzar con "imagen de".

## Entrada Esperada

- `image_description` (str, requerido): descripcion de lo que contiene la imagen
- `context` (str, opcional): contexto del caption o campana
- `language` (str, opcional): `"es"` | `"en"`, default `"es"`

## Salida Esperada

- `ok`: booleano
- `data.alt_text`: texto alternativo listo para el campo de la API
- `data.character_count`: longitud del alt text
- `data.seo_keywords`: keywords relevantes identificadas

## Ejemplo

```python
result = run({"image_description": "mujer sonriendo con laptop en cafe", "context": "productividad freelance"})
# result["data"]["alt_text"] -> "Freelancer trabajando desde cafe con laptop, productiva y motivada"
```

## Variables de entorno

- `ANTHROPIC_API_KEY`: clave de la API de Anthropic (obligatoria)
