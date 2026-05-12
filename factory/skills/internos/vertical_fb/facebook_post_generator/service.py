"""Genera variantes de post de Facebook para una vacante usando Claude."""

from __future__ import annotations

import os
import anthropic


_CLIENT = None


def _get_client() -> anthropic.Anthropic:
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _CLIENT


class FacebookPostGeneratorService:

    def ejecutar(self, context: dict) -> dict:
        titulo:       str = context.get("titulo_vacante") or context.get("titulo") or ""
        descripcion:  str = context.get("descripcion_vacante") or context.get("descripcion") or ""
        requisitos:   str = context.get("requisitos") or ""
        salario:      str = context.get("salario") or ""
        ubicacion:    str = context.get("ubicacion") or ""
        contacto:     str = context.get("contacto") or ""
        grupo_nombre: str = context.get("grupo_nombre") or ""
        variantes:    int = min(int(context.get("variantes", 3)), 5)

        if not titulo:
            return {"ok": False, "error": "titulo_vacante es requerido"}
        if not contacto:
            return {"ok": False, "error": "contacto es requerido (link Telegram/WA o telefono)"}

        prompt = self._build_prompt(
            titulo, descripcion, requisitos, salario, ubicacion, contacto, grupo_nombre, variantes
        )

        try:
            msg = _get_client().messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = msg.content[0].text.strip()
        except Exception as e:
            return {"ok": False, "error": f"Error Claude: {e}"}

        variantes_list = self._parsear_variantes(raw)
        return {
            "ok": True,
            "data": {
                "variantes":    variantes_list,
                "recomendada":  variantes_list[0] if variantes_list else raw,
                "total":        len(variantes_list),
            },
        }

    def _build_prompt(
        self,
        titulo: str,
        descripcion: str,
        requisitos: str,
        salario: str,
        ubicacion: str,
        contacto: str,
        grupo_nombre: str,
        variantes: int,
    ) -> str:
        contexto_grupo = f"El grupo se llama: {grupo_nombre}." if grupo_nombre else ""
        return f"""Eres un experto en reclutamiento de personal en México.
Genera exactamente {variantes} variantes de post para publicar en un grupo de Facebook.
{contexto_grupo}

Datos de la vacante:
- Puesto: {titulo}
- Descripción: {descripcion}
- Requisitos: {requisitos}
- Salario: {salario if salario else 'A convenir'}
- Ubicación: {ubicacion}
- Contacto: {contacto}

Reglas:
- Tono directo e informal, como habla la gente en grupos de Facebook de trabajadores
- Máximo 200 palabras por variante
- Incluir emoji moderados (3-5 por post)
- Terminar siempre con el contacto y una llamada a la acción clara
- Cada variante debe verse diferente (distinto inicio, distinto énfasis)
- Separar cada variante con la línea: ---VARIANTE---

Solo devuelve las variantes, sin explicaciones."""

    def _parsear_variantes(self, raw: str) -> list[str]:
        partes = [p.strip() for p in raw.split("---VARIANTE---") if p.strip()]
        return partes if partes else [raw]
