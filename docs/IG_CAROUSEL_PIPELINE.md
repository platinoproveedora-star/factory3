# IG Carousel Pipeline

Estado de continuidad para el motor de carruseles de Instagram en Factory3.

## Objetivo

Crear carruseles reutilizables por modo (`scientific`, `seo_educational`,
`sales`, `brand_story`, `how_to`, `myth_busting`, `case_study`) usando skills
pequenos y auditables. El modo `scientific` debe partir de fuentes reales y
generar ensayos antes de producir slides.

## Flujo actual

```text
sources + topic
-> vertical_research/research_general_essay
-> vertical_research/research_topic_essay
-> ig_carousel_research_to_claims
-> ig_carousel_copy_builder
-> ig_carousel_layout_variants
-> ig_carousel_typography_fit
-> ig_carousel_image_brief
-> ig_carousel_image_prompt
-> ig_carousel_demo_image_assets
-> ig_carousel_template_builder
-> ig_carousel_theme_guard
-> ig_render_carousel_slides
-> ig_carousel_slide_audit
-> ig_carousel_autofix_design
-> ig_carousel_quality_report
```

El skill `ig_carousel_orchestrator` coordina el flujo. En `dry_run=false`
genera carpeta con:

- `index.html`
- `slide_01.svg` ... `slide_N.svg`
- `manifest.json`
- `orchestrator_manifest.json`
- `quality_report.json`
- `assets/`
- `research/`

## Skills creados

| Skill | Estado | Funcion |
| --- | --- | --- |
| `ig_carousel_template_builder` | Implementado | Genera templates visuales, incluido `seo_hero`. |
| `ig_render_carousel_slides` | Implementado, en ajuste visual | Renderiza SVG/HTML. Acepta `image_path`/`image_url`. |
| `ig_carousel_export_assets` | Implementado | Exporta SVG/HTML/manifest. |
| `ig_carousel_image_brief` | Implementado | Define imagen/infografia por slide. |
| `ig_carousel_image_prompt` | Implementado | Convierte brief visual en prompts. |
| `ig_carousel_demo_image_assets` | Implementado | Genera assets SVG locales sin APIs externas. |
| `ig_carousel_typography_fit` | Implementado | Calcula tamanos de texto por longitud. |
| `ig_carousel_theme_guard` | Implementado | Normaliza paletas y evita negro puro. |
| `ig_carousel_layout_variants` | Implementado | Asigna roles/layouts por slide. |
| `ig_carousel_slide_audit` | Implementado | Audita densidad, fuentes y legibilidad basica. |
| `ig_carousel_autofix_design` | Implementado | Recorta texto y corrige paleta conservadoramente. |
| `ig_carousel_research_to_claims` | Implementado | Extrae claims seguros desde research. |
| `ig_carousel_copy_builder` | Implementado, en ajuste narrativo | Genera 6 slides narrativos. |
| `ig_carousel_quality_report` | Implementado | Produce score y status. |
| `ig_carousel_export_png` | Plan/validador | Verifica backend local; no agrega dependencias. |
| `ig_carousel_orchestrator` | Implementado | Coordina todo el flujo. |

## Research

La vertical `vertical_research` alimenta carruseles cientificos:

- `research_general_essay`
- `research_topic_essay`

Cada skill genera:

- ensayo completo HTML/TXT/PDF
- bibliografia JSON
- claims JSON
- analisis editorial HTML/TXT
- `editorial_package.json`

Regla dura: si no hay `sources` verificables, el skill debe devolver error y no
inventar bibliografia.

## Demos actuales

| Demo | Carpeta | Estado |
| --- | --- | --- |
| Luz matutina | `tmp/biohacking_camino_1_luz_matutina` | 6 slides, necesita revision visual humana. |
| Orden comida/glucosa | `tmp/biohacking_camino_2_orden_comida_glucosa` | 6 slides, necesita revision visual humana. |
| Demo inicial con imagenes | `tmp/ig_carousel_demo2_v2` | Legacy de prueba. |
| SEO hero | `tmp/ig_carousel_seo_hero_demo` | Legacy de template. |
| Science clean | `tmp/ig_carousel_science_demo` | Legacy de motor basico. |

## Problemas visuales abiertos

- El template `seo_hero` todavia necesita una composicion mas profesional.
- Evitar cajas que se salgan de la zona segura.
- No usar texto dentro de los assets demo como contenido principal.
- El contenido debe quedar centrado, pequeno y legible.
- El carrusel debe informar el tema con una narrativa, no repetir etiquetas de evidencia.
- Faltan layouts realmente distintos para:
  - portada
  - contexto
  - mecanismo
  - evidencia
  - aplicacion
  - cierre

## Pendientes recomendados

1. Rehacer `ig_render_carousel_slides` con layouts por `layout_role` en vez de
   un solo layout `seo_hero`.
2. Agregar auditoria de bounding boxes aproximada para detectar texto fuera de
   zona segura antes de exportar.
3. Crear un `template` editorial nuevo sin cajas fijas:
   `scientific_editorial_v2`.
4. Definir un score visual mas estricto que revise:
   - longitud por linea
   - numero de lineas
   - bloque y coordenadas
   - contraste
   - repeticion narrativa
5. Definir export PNG local cuando se autorice dependencia (`playwright` o
   `cairosvg`).

## Como continuar

Para regenerar los dos caminos biohacking actuales:

```powershell
python tmp\run_biohacking_orchestrator_paths.py
```

Antes de cerrar cambios:

```powershell
python -m py_compile <services tocados>
python -c "import json; json.load(open('factory/skills/registry.json', encoding='utf-8')); print('registry ok')"
python -c "import sys,json; sys.path.insert(0,r'factory\skills\internos\vertical_factory_utils\factory_no_hardcode_audit'); import skill; print(json.dumps(skill.run({'paths':['factory/skills/internos/vertical_instagram']}), ensure_ascii=False))"
```
