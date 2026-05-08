"""Service for rh_offer_builder — arma oferta laboral completa con IA."""

from __future__ import annotations
import json
import os


class RhOfferBuilderService:

    def ejecutar(self, context: dict) -> dict:
        valido, error = self._validar(context)
        if not valido:
            return {"ok": False, "error": error}

        puesto = context["puesto"]
        empresa = context.get("empresa", "")
        zona = context.get("zona", "")
        salario_min = context.get("salario_min")
        salario_max = context.get("salario_max")
        tipo_contrato = context.get("tipo_contrato", "indefinido")
        beneficios = context.get("beneficios", [])
        requisitos = context.get("requisitos", [])
        notas_extra = context.get("notas_extra", "")

        oferta_base = self._construir_base(
            puesto, empresa, zona, salario_min, salario_max,
            tipo_contrato, beneficios, requisitos,
        )

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            texto_ia = self._generar_con_ia(oferta_base, notas_extra, api_key)
            if texto_ia:
                oferta_base["texto_oferta"] = texto_ia
                oferta_base["generado_con_ia"] = True

        return {"ok": True, "data": oferta_base}

    def _construir_base(
        self, puesto, empresa, zona, sal_min, sal_max,
        contrato, beneficios, requisitos,
    ) -> dict:
        rango = ""
        if sal_min and sal_max:
            rango = f"${sal_min:,} - ${sal_max:,} MXN"
        elif sal_min:
            rango = f"Desde ${sal_min:,} MXN"
        elif sal_max:
            rango = f"Hasta ${sal_max:,} MXN"

        return {
            "puesto": puesto,
            "empresa": empresa,
            "zona": zona,
            "salario": rango,
            "tipo_contrato": contrato,
            "beneficios": beneficios,
            "requisitos": requisitos,
            "generado_con_ia": False,
            "texto_oferta": self._texto_fallback(puesto, empresa, zona, rango, requisitos, beneficios),
        }

    def _texto_fallback(self, puesto, empresa, zona, salario, requisitos, beneficios) -> str:
        lines = [f"SE BUSCA: {puesto.upper()}"]
        if empresa:
            lines.append(f"Empresa: {empresa}")
        if zona:
            lines.append(f"Zona: {zona}")
        if salario:
            lines.append(f"Sueldo: {salario}")
        if requisitos:
            lines.append("Requisitos: " + " | ".join(requisitos))
        if beneficios:
            lines.append("Beneficios: " + " | ".join(beneficios))
        lines.append("¡Postúlate ahora!")
        return "\n".join(lines)

    def _generar_con_ia(self, oferta: dict, notas: str, api_key: str) -> str | None:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            prompt = (
                f"Genera un texto de oferta de trabajo atractivo y directo para redes sociales.\n"
                f"Datos: {json.dumps(oferta, ensure_ascii=False)}\n"
                f"Notas adicionales: {notas}\n"
                f"Tono: operativo, directo, para trabajadores de campo. Máximo 200 palabras."
            )
            msg = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=400,
                messages=[{"role": "user", "content": prompt}],
            )
            return msg.content[0].text.strip()
        except Exception:
            return None

    def _validar(self, context: dict) -> tuple[bool, str | None]:
        if not context.get("puesto"):
            return False, "puesto es requerido"
        return True, None
