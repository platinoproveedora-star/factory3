from __future__ import annotations

import html
import json
import re
from pathlib import Path


class ResearchTopicEssayService:
    def ejecutar(self, context: dict) -> dict:
        if not isinstance(context, dict):
            return {"ok": False, "error": "context debe ser dict"}
        topic = str(context.get("topic") or "").strip()
        parent_topic = str(context.get("parent_topic") or context.get("general_topic") or "").strip()
        if not topic:
            return {"ok": False, "error": "topic requerido"}
        sources = self._valid_sources(context.get("sources"))
        if not sources:
            return {"ok": False, "error": "sources verificables requerido; no se genera bibliografia inventada"}
        essay = self._essay(context, topic, parent_topic, sources)
        files = []
        output_dir = context.get("output_dir")
        if output_dir and not context.get("dry_run", True):
            out = self._resolve_output_dir(str(output_dir))
            out.mkdir(parents=True, exist_ok=True)
            files = self._write_outputs(out, essay)
        return {"ok": True, "data": {"essay": essay, "files": files, "dry_run": bool(context.get("dry_run", True))}}

    def _essay(self, context: dict, topic: str, parent_topic: str, sources: list[dict]) -> dict:
        audience = str(context.get("audience") or "publico general adulto").strip()
        citation_style = str(context.get("citation_style") or "APA").strip().upper()
        central_claim = str(context.get("central_claim") or topic).strip()
        mechanism = str(context.get("mechanism") or "mecanismo no especificado; depende de las fuentes revisadas").strip()
        evidence = self._evidence_sections(sources)
        claims = self._claims(topic, sources)
        editorial_package = self._editorial_package(topic, audience, central_claim, sources, claims)
        return {
            "kind": "topic",
            "title": f"Ensayo cientifico especifico: {topic}",
            "topic": topic,
            "parent_topic": parent_topic,
            "central_claim": central_claim,
            "audience": audience,
            "citation_style": citation_style,
            "abstract": self._paragraph(
                f"Este ensayo profundiza en {topic} como subtema especifico.",
                "El objetivo es convertir evidencia verificable en una explicacion clara, prudente y util para contenido educativo.",
            ),
            "introduction": self._paragraph(
                f"Dentro del marco general {parent_topic or 'del tema investigado'}, {topic} permite analizar un claim mas concreto.",
                f"El claim central revisado es: {central_claim}.",
            ),
            "body": {
                "essay_sections": self._full_essay_sections(topic, audience, central_claim, mechanism, sources, evidence),
                "scientific_mechanism": self._paragraph(
                    f"El mecanismo propuesto se resume asi: {mechanism}.",
                    "Debe interpretarse segun el tipo de estudio, la poblacion y la consistencia entre fuentes.",
                ),
                "principal_findings": self._principal_findings(sources),
                "evidence": evidence,
                "real_life_applications": self._applications(topic, audience),
                "target_population": self._target_population(context, audience),
                "limitations": self._paragraph(
                    "Este subtema puede tener diferencias por edad, sexo, condicion metabolica, contexto clinico o habitos previos.",
                    "Las aplicaciones practicas deben presentarse como orientacion educativa, no como prescripcion universal.",
                ),
            },
            "conclusion": self._paragraph(
                f"{topic.capitalize()} puede transformarse en contenido de carrusel si se comunica como evidencia contextual.",
                "La pieza final debe mostrar que se sabe, que falta por confirmar y que accion prudente puede observar una persona.",
            ),
            "bibliography": [self._reference(src, citation_style) for src in sources],
            "claims_for_carousel": claims,
            "slide_outline": self._slide_outline(topic, central_claim, sources),
            "editorial_package": editorial_package,
        }

    def _full_essay_sections(self, topic: str, audience: str, central_claim: str, mechanism: str, sources: list[dict], evidence: dict) -> list[dict]:
        sections = [
            {
                "heading": "Planteamiento del tema especifico",
                "paragraphs": [
                    self._paragraph(
                        f"El subtema {topic} se aborda a partir del claim central: {central_claim}.",
                        f"Para {audience}, este enfoque permite pasar de una recomendacion viral o simplificada a una explicacion basada en fuentes concretas.",
                    ),
                    self._paragraph(
                        "Un ensayo especifico no debe limitarse a repetir el claim, sino explicar de donde viene, que mecanismo lo haria plausible y en que condiciones podria no aplicar.",
                        "Por eso se separan hallazgos, aplicacion cotidiana, poblacion enfocada y limites.",
                    ),
                ],
            },
            {
                "heading": "Mecanismo cientifico propuesto",
                "paragraphs": [
                    self._paragraph(
                        mechanism,
                        "El mecanismo debe entenderse como una explicacion funcional que conecta conducta y resultado observado, no como garantia de efecto individual.",
                    ),
                    self._paragraph(
                        "La solidez de este mecanismo depende de si las fuentes miden resultados directos, de si comparan condiciones relevantes y de si la poblacion estudiada se parece al publico objetivo.",
                        "Cuando estos elementos son parciales, el contenido debe usar lenguaje prudente.",
                    ),
                ],
            },
            {
                "heading": "Hallazgos y nivel de evidencia",
                "paragraphs": [
                    self._paragraph(
                        f"En las fuentes revisadas hay {len(evidence.get('strong') or [])} hallazgos de evidencia fuerte, {len(evidence.get('limited') or [])} limitados y {len(evidence.get('debated') or [])} debatidos.",
                        "Esta lectura ayuda a decidir que puede afirmarse en un carrusel o reel y que debe quedar como advertencia.",
                    ),
                    self._paragraph(
                        "El valor editorial no consiste en esconder las limitaciones, sino en convertirlas en confianza.",
                        "Una pieza que explica que se sabe, que no se sabe y para quien aplica suele ser mas creible que una promesa absoluta.",
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
                            str(src.get("key_findings") or src.get("summary") or "La fuente aporta evidencia especifica al tema."),
                            f"Tipo de fuente: {src.get('source_type') or 'no especificado'}. Nivel de evidencia: {self._evidence_level(src)}.",
                        ),
                        self._paragraph(
                            "Para uso en contenido, esta fuente debe convertirse en una afirmacion corta y rastreable.",
                            "La referencia debe permanecer disponible para evitar que el carrusel pierda rigor o parezca una opinion sin respaldo.",
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

    def _principal_findings(self, sources: list[dict]) -> list[dict]:
        rows = []
        for src in sources:
            finding = str(src.get("key_findings") or src.get("summary") or "").strip()
            if finding:
                rows.append({"finding": finding, "source": src.get("title")})
        return rows

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
            {"area": "decision cotidiana", "paragraph": f"Usar el aprendizaje sobre {topic} para observar patrones personales antes de generalizar conclusiones."},
            {"area": "contenido educativo", "paragraph": f"Explicar el subtema a {audience} con un claim, una evidencia, una limitacion y una accion prudente."},
            {"area": "seguimiento", "paragraph": "Convertir la recomendacion en una variable observable durante varios dias, sin prometer resultados garantizados."},
        ]

    def _target_population(self, context: dict, audience: str) -> dict:
        return {
            "audience": audience,
            "age": str(context.get("age_range") or "depende de las fuentes especificas"),
            "sex": str(context.get("sex_focus") or "sin enfoque por sexo salvo evidencia explicita"),
            "context": str(context.get("population_context") or "personas que buscan entender el subtema con base cientifica"),
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
                        "slide_hint": f"{topic} - claim {idx}",
                    }
                )
        return claims

    def _editorial_package(self, topic: str, audience: str, central_claim: str, sources: list[dict], claims: list[dict]) -> dict:
        return {
            "safe_claims": claims,
            "prohibited_claims": [
                {"claim": f"{central_claim} para todas las personas sin excepcion.", "reason": "Generalizacion absoluta no permitida."},
                {"claim": f"{topic} reemplaza atencion profesional.", "reason": "Riesgo medico/educativo; el contenido no debe sustituir asesoria."},
            ],
            "visual_data_points": self._visual_data_points(topic, sources),
            "simple_analogies": self._analogies(topic),
            "carousel_ideas": self._carousel_ideas(topic, central_claim, claims),
            "reel_script": self._reel_script(topic, central_claim, claims),
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
            return "Aplicar con contexto individual."
        if level == "debatida":
            return "Comunicar como evidencia mixta."
        return "No presentar como regla universal."

    def _visual_data_points(self, topic: str, sources: list[dict]) -> list[dict]:
        rows = []
        for src in sources[:4]:
            finding = str(src.get("key_findings") or src.get("summary") or src.get("claim") or "").strip()
            if finding:
                rows.append({"concept": self._clip(finding, 90), "visual": "diagrama claim -> mecanismo -> accion", "source_title": src.get("title")})
        return rows or [{"concept": topic, "visual": "diagrama del mecanismo", "source_title": ""}]

    def _analogies(self, topic: str) -> list[str]:
        return [
            f"{topic} puede explicarse como una perilla, no como un interruptor: cambia el grado, no garantiza el resultado.",
            "Un claim cientifico es como una silla: necesita varias patas, no una sola fuente aislada.",
        ]

    def _carousel_ideas(self, topic: str, central_claim: str, claims: list[dict]) -> dict:
        slides = [
            {"slide": 1, "headline": self._clip(topic, 56), "body": self._clip(central_claim, 110), "visual": "portada con pregunta cientifica"},
            {"slide": 2, "headline": "El claim", "body": self._clip(claims[0]["carousel_version"] if claims else central_claim, 110), "visual": "claim + fuente"},
            {"slide": 3, "headline": "Nivel de evidencia", "body": claims[0]["evidence_level"] if claims else "limitada", "visual": "semaforo de evidencia"},
            {"slide": 4, "headline": "Aplicacion prudente", "body": "Convierte el hallazgo en una observacion medible, no en promesa.", "visual": "checklist"},
        ]
        return {"hook": f"Un detalle sobre {topic} que se suele simplificar demasiado.", "slides": slides, "cta": "Guarda el resumen y revisa la fuente antes de aplicarlo."}

    def _reel_script(self, topic: str, central_claim: str, claims: list[dict]) -> dict:
        return {
            "hook_0_3s": f"Este tip sobre {topic} no es magia, es contexto.",
            "development_3_30s": [self._clip(central_claim, 150), "Revisa poblacion estudiada, mecanismo y limites antes de convertirlo en regla."],
            "close_cta": "Si quieres usarlo, mide una variable por 7 dias.",
            "on_screen_text": ["Claim", "Fuente", "Limite", "Aplicacion"],
            "visual_scenes": ["pregunta inicial", "paper/fuente", "diagrama simple", "accion medible"],
        }

    def _myths(self, topic: str) -> list[dict]:
        return [
            {"myth": f"{topic} funciona igual en todos.", "reality": "La respuesta depende de persona, contexto y comparacion estudiada."},
            {"myth": "Un resultado interesante ya es recomendacion universal.", "reality": "Primero hay que mirar nivel de evidencia y limitaciones."},
        ]

    def _faq(self, topic: str, audience: str) -> list[dict]:
        return [
            {"question": f"Quien puede aplicar {topic}?", "answer": f"{audience}, si el contexto coincide con las fuentes y se mantiene como observacion educativa."},
            {"question": "Que hago si tengo una condicion medica?", "answer": "Usar el contenido solo como informacion y consultar a un profesional."},
        ]

    def _misinterpretation_risks(self, topic: str) -> list[str]:
        return [
            f"Convertir {topic} en regla universal.",
            "Ignorar poblacion estudiada.",
            "Omitir que una fuente puede ser piloto, observacional o limitada.",
        ]

    def _glossary(self, topic: str) -> list[dict]:
        return [
            {"term": "claim central", "definition": "Afirmacion principal que el contenido va a explicar."},
            {"term": "certeza", "definition": "Confianza comunicable segun evidencia disponible."},
            {"term": topic, "definition": f"Subtema especifico revisado: {topic}."},
        ]

    def _clip(self, value: str, limit: int) -> str:
        value = re.sub(r"\s+", " ", str(value)).strip()
        return value if len(value) <= limit else value[: limit - 1].rstrip() + "..."

    def _slide_outline(self, topic: str, central_claim: str, sources: list[dict]) -> list[dict]:
        return [
            {"kind": "cover", "headline": topic, "body": central_claim},
            {"kind": "evidence", "headline": "Que dice la evidencia", "body": str((sources[0].get("key_findings") or sources[0].get("summary") or sources[0].get("title")) if sources else "")},
            {"kind": "application", "headline": "Como se aplica", "body": "Traducir el hallazgo en una accion observable y prudente."},
            {"kind": "limits", "headline": "Lo que aun no sabemos", "body": "Mostrar limites, poblaciones estudiadas y nivel de certeza."},
        ]

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
            "research_topic_essay.html": html_text,
            "research_topic_essay.txt": text,
            "topic_bibliography.json": json.dumps(essay["bibliography"], ensure_ascii=True, indent=2),
            "topic_claims.json": json.dumps(essay["claims_for_carousel"], ensure_ascii=True, indent=2),
            "topic_slide_outline.json": json.dumps(essay["slide_outline"], ensure_ascii=True, indent=2),
            "topic_editorial_package.json": json.dumps(essay["editorial_package"], ensure_ascii=True, indent=2),
            "research_topic_info_analysis.html": self._analysis_html(essay),
            "research_topic_info_analysis.txt": self._analysis_text(essay),
        }
        paths = []
        for filename, content in files.items():
            path = out / filename
            path.write_text(content, encoding="utf-8")
            paths.append(str(path))
        pdf_path = out / "research_topic_essay.pdf"
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
        body.append("<h2>Hallazgos principales</h2>")
        for row in essay["body"]["principal_findings"]:
            body.append(f"<p>{html.escape(row['finding'])} <i>{html.escape(str(row['source']))}</i></p>")
        body.append("<h2>Aplicaciones reales a la vida</h2>")
        for row in essay["body"]["real_life_applications"]:
            body.append(f"<p><b>{html.escape(row['area'])}.</b> {html.escape(row['paragraph'])}</p>")
        body.append(f"<h2>Personas enfocadas</h2><p>{html.escape(json.dumps(essay['body']['target_population'], ensure_ascii=False))}</p>")
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
        lines.extend(["", "HALLAZGOS"])
        for row in essay["body"]["principal_findings"]:
            lines.append(f"- {row['finding']} ({row['source']})")
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
