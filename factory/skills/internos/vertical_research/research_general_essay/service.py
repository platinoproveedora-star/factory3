from __future__ import annotations

import html
import json
import re
from pathlib import Path


class ResearchGeneralEssayService:
    def ejecutar(self, context: dict) -> dict:
        if not isinstance(context, dict):
            return {"ok": False, "error": "context debe ser dict"}
        topic = str(context.get("topic") or "").strip()
        if not topic:
            return {"ok": False, "error": "topic requerido"}
        sources = self._valid_sources(context.get("sources"))
        if not sources:
            return {"ok": False, "error": "sources verificables requerido; no se genera bibliografia inventada"}
        essay = self._essay(context, topic, sources)
        files = []
        output_dir = context.get("output_dir")
        if output_dir and not context.get("dry_run", True):
            out = self._resolve_output_dir(str(output_dir))
            out.mkdir(parents=True, exist_ok=True)
            files = self._write_outputs(out, essay)
        return {"ok": True, "data": {"essay": essay, "files": files, "dry_run": bool(context.get("dry_run", True))}}

    def _essay(self, context: dict, topic: str, sources: list[dict]) -> dict:
        audience = str(context.get("audience") or "publico general adulto").strip()
        citation_style = str(context.get("citation_style") or "APA").strip().upper()
        subtopics = context.get("subtopics") if isinstance(context.get("subtopics"), list) else self._subtopics(topic, sources)
        evidence = self._evidence_sections(sources)
        claims = self._claims(topic, sources)
        editorial_package = self._editorial_package(topic, audience, sources, claims)
        return {
            "kind": "general",
            "title": f"Ensayo cientifico general: {topic}",
            "topic": topic,
            "audience": audience,
            "citation_style": citation_style,
            "abstract": self._paragraph(
                f"Este ensayo introduce el tema {topic} desde una perspectiva educativa y basada en fuentes verificables.",
                "Resume los principales subtemas investigados, sus aplicaciones practicas y las limitaciones de la evidencia disponible.",
            ),
            "introduction": self._paragraph(
                f"{topic.capitalize()} es un campo de interes porque conecta mecanismos biologicos, conducta y decisiones cotidianas.",
                f"Para una audiencia de {audience}, el objetivo es distinguir hallazgos respaldados por investigacion de afirmaciones aun inciertas.",
            ),
            "body": {
                "essay_sections": self._full_essay_sections(topic, audience, sources, subtopics, evidence),
                "researched_subtopics": [
                    {
                        "subtitle": str(item),
                        "paragraph": self._paragraph(
                            f"El subtema {item} aparece como una linea relevante dentro de la literatura revisada.",
                            "Su interpretacion debe considerar diseno de estudio, poblacion analizada y consistencia entre fuentes.",
                        ),
                    }
                    for item in subtopics[:6]
                ],
                "evidence": evidence,
                "real_life_applications": self._applications(topic, audience),
                "target_population": self._target_population(context, audience),
                "limitations": self._paragraph(
                    "La evidencia debe leerse con prudencia: no todos los estudios tienen el mismo nivel de causalidad, tamano muestral o aplicabilidad externa.",
                    "Cuando una conclusion depende de poblaciones especificas, intervenciones cortas o medidas indirectas, se clasifica como evidencia limitada.",
                ),
            },
            "conclusion": self._paragraph(
                f"En conjunto, la investigacion disponible permite abordar {topic} como un tema aplicable pero dependiente del contexto.",
                "La mejor traduccion a contenido educativo es comunicar beneficios plausibles, limites y acciones observables sin prometer resultados universales.",
            ),
            "bibliography": [self._reference(src, citation_style) for src in sources],
            "claims_for_carousel": claims,
            "editorial_package": editorial_package,
        }

    def _full_essay_sections(self, topic: str, audience: str, sources: list[dict], subtopics: list[str], evidence: dict) -> list[dict]:
        sections = [
            {
                "heading": "Marco general del tema",
                "paragraphs": [
                    self._paragraph(
                        f"El estudio de {topic} exige mirar la relacion entre conducta, fisiologia y contexto.",
                        f"Para {audience}, el valor de este tema no esta en encontrar una regla unica, sino en comprender que variables tienen respaldo suficiente para convertirse en habitos observables.",
                    ),
                    self._paragraph(
                        "La literatura revisada sugiere que los efectos practicos suelen depender del momento, la dosis, la poblacion estudiada y la forma en que se mide el resultado.",
                        "Por eso, el ensayo distingue entre hallazgos consistentes, evidencia limitada y afirmaciones que todavia requieren prudencia.",
                    ),
                ],
            },
            {
                "heading": "Principales subtemas investigados",
                "paragraphs": [
                    self._paragraph(
                        "Los subtemas principales encontrados son: " + ", ".join(str(item) for item in subtopics[:6]) + ".",
                        "Estos ejes permiten ordenar la informacion sin reducir el tema a un consejo aislado.",
                    ),
                    self._paragraph(
                        "Cada subtema debe interpretarse a partir del tipo de fuente disponible.",
                        "Una declaracion de posicion, un estudio experimental, una revision o un estudio piloto no aportan el mismo grado de certeza, aunque todos puedan orientar buenas preguntas de investigacion y comunicacion.",
                    ),
                ],
            },
            {
                "heading": "Evidencia disponible y nivel de certeza",
                "paragraphs": [
                    self._paragraph(
                        f"En las fuentes analizadas se identificaron {len(evidence.get('strong') or [])} hallazgos de evidencia fuerte, {len(evidence.get('limited') or [])} de evidencia limitada y {len(evidence.get('debated') or [])} debatidos.",
                        "Esta clasificacion no pretende cerrar el tema, sino evitar que una observacion prometedora se presente como conclusion universal.",
                    ),
                    self._paragraph(
                        "Cuando la evidencia es limitada, el contenido debe formularse con verbos prudentes como puede, se asocia, sugiere o en ciertos contextos.",
                        "Cuando la evidencia es mas fuerte, aun asi conviene explicar para que poblacion aplica y que condiciones quedan fuera del alcance del material.",
                    ),
                ],
            },
        ]
        for src in sources[:4]:
            sections.append(
                {
                    "heading": str(src.get("title") or "Fuente revisada"),
                    "paragraphs": [
                        self._paragraph(
                            str(src.get("key_findings") or src.get("summary") or "La fuente aporta informacion relevante al tema."),
                            f"Tipo de fuente: {src.get('source_type') or 'no especificado'}. Nivel de evidencia: {self._evidence_level(src)}.",
                        ),
                        self._paragraph(
                            "Su utilidad editorial consiste en transformar el hallazgo en un claim preciso, acompañado de una advertencia sobre limites.",
                            "De esta manera el contenido final puede ser atractivo sin perder rigor.",
                        ),
                    ],
                }
            )
        return sections

    def _valid_sources(self, raw: object) -> list[dict]:
        if not isinstance(raw, list):
            return []
        sources = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            locator = item.get("doi") or item.get("url") or item.get("pmid") or item.get("source_id")
            if title and locator:
                sources.append(item)
        return sources

    def _subtopics(self, topic: str, sources: list[dict]) -> list[str]:
        found = []
        for src in sources:
            for key in ("topics", "keywords"):
                values = src.get(key)
                if isinstance(values, list):
                    found.extend(str(v).strip() for v in values if str(v).strip())
        return found or [f"mecanismos de {topic}", "evidencia observacional", "intervenciones practicas", "limitaciones metodologicas"]

    def _evidence_sections(self, sources: list[dict]) -> dict:
        strong, limited, debated = [], [], []
        for src in sources:
            strength = str(src.get("evidence_strength") or "limited").lower()
            finding = str(src.get("key_findings") or src.get("summary") or src.get("title") or "").strip()
            row = {"source": src.get("title"), "finding": finding}
            if strength in {"strong", "alta", "high"}:
                strong.append(row)
            elif strength in {"debated", "mixta", "mixed"}:
                debated.append(row)
            else:
                limited.append(row)
        return {"strong": strong, "limited": limited, "debated": debated}

    def _applications(self, topic: str, audience: str) -> list[dict]:
        return [
            {"area": "educacion personal", "paragraph": f"Usar {topic} para tomar mejores decisiones cotidianas sin convertir evidencia limitada en reglas absolutas."},
            {"area": "habitos", "paragraph": f"Traducir hallazgos a observaciones medibles y cambios pequenos adecuados para {audience}."},
            {"area": "comunicacion", "paragraph": "Explicar riesgos, beneficios y limites con lenguaje claro para evitar exageraciones."},
        ]

    def _target_population(self, context: dict, audience: str) -> dict:
        return {
            "audience": audience,
            "age": str(context.get("age_range") or "depende del tema y las fuentes revisadas"),
            "sex": str(context.get("sex_focus") or "sin restriccion salvo que las fuentes indiquen diferencias por sexo"),
            "context": str(context.get("population_context") or "personas interesadas en contenido educativo basado en evidencia"),
        }

    def _claims(self, topic: str, sources: list[dict]) -> list[dict]:
        claims = []
        for idx, src in enumerate(sources[:8], start=1):
            text = str(src.get("claim") or src.get("key_findings") or src.get("summary") or "").strip()
            if text:
                claims.append(
                    {
                        "claim": text,
                        "source_title": src.get("title"),
                        "evidence_level": self._evidence_level(src),
                        "certainty": self._certainty(src),
                        "warning": self._warning(src),
                        "carousel_version": self._clip(text, 96),
                        "reel_version": self._clip(text, 150),
                        "slide_hint": f"{topic} - idea {idx}",
                    }
                )
        return claims

    def _editorial_package(self, topic: str, audience: str, sources: list[dict], claims: list[dict]) -> dict:
        safe_claims = claims
        prohibited_claims = [
            {
                "claim": f"{topic} cura o garantiza resultados universales.",
                "reason": "Promesa absoluta no sustentada; puede ser riesgosa o engañosa.",
            },
            {
                "claim": "Todas las personas deben aplicar la misma recomendacion.",
                "reason": "Ignora edad, sexo, condiciones, contexto clinico y variabilidad individual.",
            },
        ]
        return {
            "safe_claims": safe_claims,
            "prohibited_claims": prohibited_claims,
            "visual_data_points": self._visual_data_points(topic, sources),
            "simple_analogies": self._analogies(topic),
            "carousel_ideas": self._carousel_ideas(topic, safe_claims),
            "reel_script": self._reel_script(topic, safe_claims),
            "myths_vs_reality": self._myths(topic),
            "faq": self._faq(topic, audience),
            "misinterpretation_risks": self._misinterpretation_risks(topic),
            "glossary": self._glossary(topic),
            "source_map": [{"source_title": src.get("title"), "locator": src.get("doi") or src.get("url") or src.get("pmid") or src.get("source_id")} for src in sources],
        }

    def _evidence_level(self, src: dict) -> str:
        strength = str(src.get("evidence_strength") or "limited").lower()
        if strength in {"strong", "alta", "high"}:
            return "fuerte"
        if strength in {"moderate", "moderada", "medium"}:
            return "moderada"
        if strength in {"debated", "mixta", "mixed"}:
            return "debatida"
        return "limitada"

    def _certainty(self, src: dict) -> str:
        level = self._evidence_level(src)
        return {"fuerte": "alta", "moderada": "media", "limitada": "baja-media", "debatida": "variable"}.get(level, "baja-media")

    def _warning(self, src: dict) -> str:
        level = self._evidence_level(src)
        if level == "fuerte":
            return "Aun asi, adaptar a contexto individual."
        if level == "debatida":
            return "Presentar como evidencia mixta, no como conclusion cerrada."
        return "Presentar como posible asociacion o hallazgo contextual."

    def _visual_data_points(self, topic: str, sources: list[dict]) -> list[dict]:
        rows = []
        for src in sources[:6]:
            finding = str(src.get("key_findings") or src.get("summary") or src.get("claim") or "").strip()
            if finding:
                rows.append({"concept": self._clip(finding, 90), "visual": "comparacion, proceso o barra de evidencia", "source_title": src.get("title")})
        return rows or [{"concept": topic, "visual": "mapa de subtemas", "source_title": ""}]

    def _analogies(self, topic: str) -> list[str]:
        return [
            f"Pensar en {topic} como un tablero de control: una sola palanca rara vez explica todo.",
            "La evidencia funciona como un semaforo: verde para lo consistente, amarillo para lo prometedor y rojo para lo exagerado.",
        ]

    def _carousel_ideas(self, topic: str, claims: list[dict]) -> dict:
        slides = [{"slide": 1, "headline": f"{topic}: lo que si dice la ciencia", "body": "Separar evidencia de exageracion.", "visual": "portada editorial con keyword"}]
        for idx, claim in enumerate(claims[:5], start=2):
            slides.append({"slide": idx, "headline": self._clip(claim["carousel_version"], 52), "body": f"Evidencia: {claim['evidence_level']}.", "visual": "claim + fuente + takeaway"})
        slides.append({"slide": len(slides) + 1, "headline": "Aplicalo con prudencia", "body": "Observa una variable y evita promesas absolutas.", "visual": "checklist"})
        return {"hook": f"No todo lo que se dice sobre {topic} tiene el mismo respaldo.", "slides": slides, "cta": "Guarda esta guia y revisa las fuentes."}

    def _reel_script(self, topic: str, claims: list[dict]) -> dict:
        first = claims[0]["reel_version"] if claims else f"{topic} tiene matices importantes."
        return {
            "hook_0_3s": f"Sobre {topic}, cuidado con las promesas faciles.",
            "development_3_30s": [first, "La clave es mirar nivel de evidencia, poblacion estudiada y limites."],
            "close_cta": "Guarda esto antes de convertir un tip en regla universal.",
            "on_screen_text": ["Evidencia no es lo mismo que promesa", "Mira fuentes, limites y contexto"],
            "visual_scenes": ["portada con pregunta", "claim con fuente", "semaforo de evidencia", "CTA"],
        }

    def _myths(self, topic: str) -> list[dict]:
        return [
            {"myth": f"Sobre {topic} hay una regla unica para todos.", "reality": "La aplicacion depende de poblacion, contexto y nivel de evidencia."},
            {"myth": "Si aparece en un estudio, ya esta comprobado para todos.", "reality": "Un estudio es una pieza; importa el conjunto de evidencia."},
        ]

    def _faq(self, topic: str, audience: str) -> list[dict]:
        return [
            {"question": f"Esto aplica para {audience}?", "answer": "Aplica como orientacion educativa si las fuentes estudiaron poblaciones comparables."},
            {"question": f"Puedo tomar decisiones solo con este ensayo sobre {topic}?", "answer": "No; sirve para educacion y para formular mejores preguntas."},
        ]

    def _misinterpretation_risks(self, topic: str) -> list[str]:
        return [
            f"Presentar {topic} como solucion garantizada.",
            "Omitir limitaciones de poblacion o diseno de estudio.",
            "Convertir una asociacion en causalidad sin respaldo suficiente.",
        ]

    def _glossary(self, topic: str) -> list[dict]:
        return [
            {"term": "nivel de evidencia", "definition": "Grado de confianza segun tipo, calidad y consistencia de estudios."},
            {"term": "claim", "definition": "Afirmacion concreta que puede usarse en contenido si esta ligada a fuente."},
            {"term": topic, "definition": f"Tema central revisado en este ensayo: {topic}."},
        ]

    def _clip(self, value: str, limit: int) -> str:
        value = re.sub(r"\s+", " ", str(value)).strip()
        return value if len(value) <= limit else value[: limit - 1].rstrip() + "..."

    def _reference(self, src: dict, style: str) -> str:
        authors = src.get("authors")
        if isinstance(authors, list):
            authors_text = ", ".join(str(a) for a in authors)
        else:
            authors_text = str(authors or "Autor no especificado")
        year = str(src.get("year") or "s. f.")
        title = str(src.get("title") or "").strip()
        journal = str(src.get("journal") or src.get("publisher") or "").strip()
        locator = str(src.get("doi") or src.get("url") or src.get("pmid") or src.get("source_id") or "").strip()
        if style == "VANCOUVER":
            return f"{authors_text}. {title}. {journal}. {year}. {locator}".strip()
        return f"{authors_text} ({year}). {title}. {journal}. {locator}".strip()

    def _paragraph(self, *parts: str) -> str:
        return " ".join(part.strip() for part in parts if part and part.strip())

    def _write_outputs(self, out: Path, essay: dict) -> list[str]:
        html_text = self._html(essay)
        text = self._plain_text(essay)
        files = {
            "research_general_essay.html": html_text,
            "research_general_essay.txt": text,
            "bibliography.json": json.dumps(essay["bibliography"], ensure_ascii=True, indent=2),
            "claims.json": json.dumps(essay["claims_for_carousel"], ensure_ascii=True, indent=2),
            "editorial_package.json": json.dumps(essay["editorial_package"], ensure_ascii=True, indent=2),
            "research_general_info_analysis.html": self._analysis_html(essay),
            "research_general_info_analysis.txt": self._analysis_text(essay),
        }
        paths = []
        for filename, content in files.items():
            path = out / filename
            path.write_text(content, encoding="utf-8")
            paths.append(str(path))
        pdf_path = out / "research_general_essay.pdf"
        self._write_basic_pdf(pdf_path, text)
        paths.append(str(pdf_path))
        return paths

    def _html(self, essay: dict) -> str:
        body = [f"<h1>{html.escape(essay['title'])}</h1>", f"<p><b>Resumen.</b> {html.escape(essay['abstract'])}</p>", f"<h2>Introduccion</h2><p>{html.escape(essay['introduction'])}</p>"]
        body.append("<h2>Cuerpo</h2>")
        for section in essay["body"]["essay_sections"]:
            body.append(f"<h3>{html.escape(section['heading'])}</h3>")
            for paragraph in section["paragraphs"]:
                body.append(f"<p>{html.escape(paragraph)}</p>")
        body.append("<h2>Aplicaciones reales a la vida</h2>")
        for row in essay["body"]["real_life_applications"]:
            body.append(f"<p><b>{html.escape(row['area'])}.</b> {html.escape(row['paragraph'])}</p>")
        pop = essay["body"]["target_population"]
        body.append(f"<h2>Personas enfocadas</h2><p>{html.escape(json.dumps(pop, ensure_ascii=False))}</p>")
        body.append(f"<h2>Limitaciones</h2><p>{html.escape(essay['body']['limitations'])}</p>")
        body.append(f"<h2>Conclusion</h2><p>{html.escape(essay['conclusion'])}</p>")
        body.append("<h2>Referencias</h2><ol>" + "".join(f"<li>{html.escape(ref)}</li>" for ref in essay["bibliography"]) + "</ol>")
        return "<!doctype html><html><head><meta charset='utf-8'><style>body{font-family:Georgia,serif;max-width:860px;margin:44px auto;line-height:1.7;color:#1f2937}h1,h2{font-family:Arial,sans-serif;color:#0f3f46}h3{font-family:Arial,sans-serif;color:#245c63}</style></head><body>" + "\n".join(body) + "</body></html>"

    def _analysis_html(self, essay: dict) -> str:
        body = [f"<h1>Analisis editorial: {html.escape(essay['topic'])}</h1>"]
        body.append("<h2>Claims seguros</h2><ul>" + "".join(f"<li>{html.escape(row['carousel_version'])} <b>({html.escape(row['evidence_level'])})</b></li>" for row in essay["editorial_package"]["safe_claims"]) + "</ul>")
        body.append("<h2>Ideas para carrusel</h2><ol>" + "".join(f"<li>{html.escape(row['headline'])}: {html.escape(row['body'])}</li>" for row in essay["editorial_package"]["carousel_ideas"]["slides"]) + "</ol>")
        body.append(f"<h2>Reel</h2><p>{html.escape(essay['editorial_package']['reel_script']['hook_0_3s'])}</p>")
        body.append("<h2>Riesgos de interpretacion</h2><ul>" + "".join(f"<li>{html.escape(row)}</li>" for row in essay["editorial_package"]["misinterpretation_risks"]) + "</ul>")
        return "<!doctype html><html><head><meta charset='utf-8'><style>body{font-family:Arial,sans-serif;max-width:860px;margin:40px auto;line-height:1.55;color:#1f2937}h1,h2{color:#0f3f46}</style></head><body>" + "\n".join(body) + "</body></html>"

    def _analysis_text(self, essay: dict) -> str:
        return json.dumps(essay["editorial_package"], ensure_ascii=False, indent=2)

    def _plain_text(self, essay: dict) -> str:
        lines = [essay["title"], "", "RESUMEN", essay["abstract"], "", "INTRODUCCION", essay["introduction"], "", "CUERPO"]
        for section in essay["body"]["essay_sections"]:
            lines.extend(["", section["heading"]])
            lines.extend(section["paragraphs"])
        lines.extend(["", "APLICACIONES REALES"])
        for row in essay["body"]["real_life_applications"]:
            lines.append(f"{row['area']}: {row['paragraph']}")
        lines.extend(["", "PERSONAS ENFOCADAS", json.dumps(essay["body"]["target_population"], ensure_ascii=False), "", "CONCLUSION", essay["conclusion"], "", "BIBLIOGRAFIA"])
        lines.extend(essay["bibliography"])
        return "\n".join(lines)

    def _write_basic_pdf(self, path: Path, text: str) -> None:
        lines = []
        for raw in text.splitlines():
            wrapped = re.findall(r".{1,88}(?:\s+|$)", raw) or [raw]
            lines.extend(line.strip() for line in wrapped)
        objects = [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        ]
        page_object_numbers = []
        for page_lines in self._chunks(lines, 48):
            content = ["BT", "/F1 10 Tf", "50 780 Td"]
            for idx, line in enumerate(page_lines):
                if idx:
                    content.append("0 -14 Td")
                safe = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
                content.append(f"({safe}) Tj")
            content.append("ET")
            stream = "\n".join(content).encode("latin-1", errors="replace")
            page_num = len(objects) + 2
            content_num = len(objects) + 3
            page_object_numbers.append(page_num)
            objects.append(
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> /Contents {content_num} 0 R >>".encode(
                    "ascii"
                )
            )
            objects.append(b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream")
        kids = " ".join(f"{num} 0 R" for num in page_object_numbers)
        objects.insert(1, f"<< /Type /Pages /Kids [{kids}] /Count {len(page_object_numbers)} >>".encode("ascii"))
        pdf = [b"%PDF-1.4\n"]
        offsets = []
        for idx, obj in enumerate(objects, start=1):
            offsets.append(sum(len(part) for part in pdf))
            pdf.append(f"{idx} 0 obj\n".encode("ascii") + obj + b"\nendobj\n")
        xref = sum(len(part) for part in pdf)
        pdf.append(f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode("ascii"))
        for off in offsets:
            pdf.append(f"{off:010d} 00000 n \n".encode("ascii"))
        pdf.append(f"trailer << /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode("ascii"))
        path.write_bytes(b"".join(pdf))

    def _chunks(self, values: list[str], size: int) -> list[list[str]]:
        if not values:
            return [[]]
        return [values[idx : idx + size] for idx in range(0, len(values), size)]

    def _resolve_output_dir(self, value: str) -> Path:
        root = Path(__file__).resolve().parents[5]
        path = Path(value)
        if not path.is_absolute():
            path = root / path
        return path
