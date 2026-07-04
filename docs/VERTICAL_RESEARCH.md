# vertical_research

Genera documentos de investigacion verificable para alimentar contenido educativo,
carruseles cientificos, reportes y piezas editoriales.

## Reglas

- No inventar autores, DOI, journals, titulos, URLs ni anios.
- Si no hay fuentes verificables en `context.sources`, devolver error.
- Separar evidencia fuerte, evidencia limitada y temas debatidos.
- Mantener tono educativo; no dar recomendaciones medicas absolutas.
- Escribir archivos solo con `dry_run=false`.

## Skills iniciales

| Skill | Descripcion |
| --- | --- |
| `vertical_research/research_general_essay` | Ensayo general sobre un tema amplio con estructura cientifica y bibliografia real provista. |
| `vertical_research/research_topic_essay` | Ensayo especifico sobre un subtema o claim para alimentar carruseles cientificos. |

## Salidas actuales

Cada research skill debe separar dos productos:

1. Ensayo completo:
   - `research_general_essay.html/txt/pdf`
   - `research_topic_essay.html/txt/pdf`
   - introduccion, cuerpo en prosa, aplicaciones, poblacion enfocada,
     conclusion y referencias.
2. Analisis editorial:
   - `research_general_info_analysis.html/txt`
   - `research_topic_info_analysis.html/txt`
   - claims seguros, claims prohibidos, ideas para carrusel, ideas para reel,
     mitos, FAQ, riesgos de mala interpretacion y glosario.

El ensayo no debe parecer indice ni ficha tecnica. Debe leerse como documento
entregable sobre el tema. El analisis editorial vive aparte para alimentar
carruseles, reels y otros formatos.

## Fuentes esperadas

Cada fuente debe incluir al menos `title` y uno de: `doi`, `url`, `pmid` o
`source_id`. Se recomiendan tambien `authors`, `year`, `journal`,
`source_type`, `summary` y `key_findings`.
