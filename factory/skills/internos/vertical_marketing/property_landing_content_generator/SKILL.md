# vertical_marketing/property_landing_content_generator

Genera contenido estructurado para una landing inmobiliaria dinamica.

## Input

- `property`: datos de propiedad
- `campaign`: datos de campana
- `company_id`
- `tone`, default `profesional inmobiliario`
- `dry_run`, default `true`

## Output

Devuelve campos compatibles con `landing_config.json`: titulo, SEO,
beneficios, datos clave, bloque de inversion, contacto y CTA.

Debe evitar promesas de rendimiento garantizado. Si menciona renta, presentarla
como dato actual reportado y recomendar revision documental.
