"""Service for rh_ad_copy_generator — genera copy de anuncio de reclutamiento."""

from __future__ import annotations
import os


_VARIANTES_DEFAULT = 2

_TONOS = {
    "operativo": "directo, sin rodeos, para trabajadores de campo y operadores",
    "motivacional": "energético y aspiracional, enfocado en ingresos y estabilidad",
    "urgente": "con sentido de urgencia, plazas limitadas, acción inmediata",
}


class RhAdCopyGeneratorService:

    def ejecutar(self, context: dict) -> dict:
        valido, error = self._validar(context)
        if not valido:
            return {"ok": False, "error": error}

        puesto = context["puesto"]
        empresa = context.get("empresa", "")
        zona = context.get("zona", "")
        salario = context.get("salario", "")
        requisitos = context.get("requisitos", [])
        beneficios = context.get("beneficios", [])
        tono = context.get("tono", "operativo")
        canal = context.get("canal", "facebook")
        variantes = int(context.get("variantes", _VARIANTES_DEFAULT))
        link_bot = context.get("link_bot", "")

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return {"ok": False, "error": "ANTHROPIC_API_KEY no configurada"}

        copies = self._generar_copies(
            puesto, empresa, zona, salario, requisitos,
            beneficios, tono, canal, variantes, link_bot, api_key,
        )
        return {"ok": True, "data": {"copies": copies, "canal": canal, "tono": tono}}

    def _generar_copies(
        self, puesto, empresa, zona, salario, requisitos,
        beneficios, tono, canal, variantes, link_bot, api_key,
    ) -> list[str]:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)

            desc_tono = _TONOS.get(tono, _TONOS["operativo"])
            req_str = ", ".join(requisitos) if requisitos else "no especificados"
            ben_str = ", ".join(beneficios) if beneficios else "no especificados"
            link_str = f"\nLink de postulación: {link_bot}" if link_bot else ""

            prompt = (
                f"Eres un experto en reclutamiento masivo de trabajadores operativos en México.\n"
                f"Genera {variantes} variantes de anuncio de reclutamiento para {canal}.\n\n"
                f"Puesto: {puesto}\n"
                f"Empresa: {empresa or 'empresa confidencial'}\n"
                f"Zona: {zona or 'a definir'}\n"
                f"Salario: {salario or 'a convenir'}\n"
                f"Requisitos: {req_str}\n"
                f"Beneficios: {ben_str}\n"
                f"Tono: {desc_tono}\n"
                f"{link_str}\n\n"
                f"Formato: devuelve exactamente {variantes} anuncios separados por '---'.\n"
                f"Cada anuncio máximo 150 palabras. Incluye emojis apropiados."
            )

            msg = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=800,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = msg.content[0].text.strip()
            partes = [p.strip() for p in raw.split("---") if p.strip()]
            return partes[:variantes]
        except Exception as e:
            return [f"Error generando copy: {e}"]

    def _validar(self, context: dict) -> tuple[bool, str | None]:
        if not context.get("puesto"):
            return False, "puesto es requerido"
        tono = context.get("tono", "operativo")
        if tono not in _TONOS:
            return False, f"tono inválido: {tono}. Válidos: {list(_TONOS.keys())}"
        return True, None
