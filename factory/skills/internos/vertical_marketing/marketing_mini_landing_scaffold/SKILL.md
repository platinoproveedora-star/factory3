# vertical_marketing/marketing_mini_landing_scaffold

Crea una mini landing estatica y reusable para campanas. La salida es HTML simple listo para Render Static Site, GitHub Pages, Netlify o cualquier hosting estatico.

## Entradas

- `company_id` o `empresa_id`
- `campaign_slug`
- `title`
- `description`
- `offer`
- `bullets`
- `facts`
- `image_url`
- `whatsapp_number`
- `whatsapp_message`
- `privacy_url`
- `output_dir`
- `dry_run`, default `true`

Si existe `companies/{company_id}/{campaign_slug}.json`, el skill puede hidratar titulo, descripcion y datos principales desde ese archivo.

## Salidas

- `index.html`
- `render.yaml`
- `missing_recommended_fields`
- `cta_url`

El skill no lanza pauta ni publica el sitio. Solo crea los artefactos estaticos para que otro flujo los despliegue.
