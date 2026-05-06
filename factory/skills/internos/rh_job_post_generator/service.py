"""Service for rh_job_post_generator - generates job posting text using AI."""

from __future__ import annotations

import json
import os
import urllib.request


class RhJobPostGeneratorService:

    def ejecutar(self, context: dict) -> dict:
        puesto    = context.get("puesto", "").strip()
        empresa   = context.get("empresa", "").strip()

        if not puesto:
            return {"ok": False, "error": "puesto es requerido"}
        if not empresa:
            return {"ok": False, "error": "empresa es requerido"}

        if context.get("dry_run", False):
            return {"ok": True, "message": "dry_run", "data": context}

        canal         = context.get("canal", "telegram")
        sector        = context.get("sector", "")
        requisitos    = context.get("requisitos", [])
        salario       = context.get("salario", "")
        ubicacion     = context.get("ubicacion", "")
        extras        = context.get("extras", "")

        system = (
            "Eres un especialista en reclutamiento. Redactas vacantes claras, atractivas y directas "
            "para captar candidatos calificados. Siempre respondes en JSON valido sin bloques de codigo."
        )

        req_txt    = "\n".join(f"- {r}" for r in requisitos) if requisitos else "No especificados"
        canal_note = "Formato conciso para Telegram/WhatsApp." if canal in ("telegram", "whatsapp") else "Formato completo."

        prompt = (
            f"Genera una publicacion de vacante para:\n"
            f"Puesto: {puesto}\n"
            f"Empresa: {empresa}\n"
            f"{f'Sector: {sector}' if sector else ''}\n"
            f"{f'Ubicacion: {ubicacion}' if ubicacion else ''}\n"
            f"{f'Salario: {salario}' if salario else ''}\n"
            f"Requisitos:\n{req_txt}\n"
            f"{f'Notas extra: {extras}' if extras else ''}\n"
            f"{canal_note}\n\n"
            "Devuelve unicamente este JSON:\n"
            '{"titulo": "...", "descripcion": "...", "requisitos_texto": "...", "cta": "...", "texto_completo": "..."}'
        )

        try:
            raw  = self._call_anthropic(prompt, system)
            data = json.loads(self._strip_code_block(raw))
            return {"ok": True, "message": f"vacante '{puesto}' generada", "data": data}
        except json.JSONDecodeError:
            return {"ok": False, "error": f"IA devolvio JSON invalido: {raw}"}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _strip_code_block(self, text: str) -> str:
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1]
            if text.endswith("```"):
                text = text[:-3]
        return text.strip()

    def _call_anthropic(self, prompt: str, system: str) -> str:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY no configurada")
        payload = {
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 1024,
            "system": system,
            "messages": [{"role": "user", "content": prompt}],
        }
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "content-type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=45) as response:
            result = json.loads(response.read().decode("utf-8"))
        parts = [item.get("text", "") for item in result.get("content", []) if item.get("type") == "text"]
        return "\n".join(p for p in parts if p).strip()
