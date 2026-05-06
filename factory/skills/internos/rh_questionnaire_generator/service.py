"""Service for rh_questionnaire_generator - generates and persists candidate questionnaire."""

from __future__ import annotations

import json
import os
import urllib.request

from factory.engine import SupabaseClient

_PROFUNDIDADES = {"simple", "medio", "robusto", "custom"}
_N_PREGUNTAS   = {"simple": 5, "medio": 10, "robusto": 20}


class RhQuestionnaireGeneratorService:

    def ejecutar(self, context: dict) -> dict:
        puesto      = context.get("puesto", "").strip()
        empresa_id  = context.get("empresa_id", "").strip()
        profundidad = context.get("profundidad", "simple").strip()

        if not puesto:
            return {"ok": False, "error": "puesto es requerido"}
        if not empresa_id:
            return {"ok": False, "error": "empresa_id es requerido"}
        if profundidad not in _PROFUNDIDADES:
            return {"ok": False, "error": f"profundidad invalida — validas: {', '.join(_PROFUNDIDADES)}"}

        if context.get("dry_run", False):
            return {"ok": True, "message": "dry_run", "data": context}

        vacante_id = context.get("vacante_id", "").strip() or None
        canal      = context.get("canal", "telegram")
        db         = SupabaseClient(context)

        # Buscar cuestionario existente para esta vacante
        if vacante_id:
            existing = self._buscar_existente(db, vacante_id)
            if existing.get("ok") and existing.get("data"):
                c = existing["data"]
                return {
                    "ok": True,
                    "message": f"{len(c['preguntas'])} preguntas recuperadas de Supabase (existente)",
                    "data": {
                        "cuestionario_id": c["id"],
                        "puesto":          c["puesto"],
                        "profundidad":     c["profundidad"],
                        "canal":           c.get("canal", canal),
                        "preguntas":       c["preguntas"],
                        "generado_ahora":  False,
                    },
                }

        # Generar con IA
        sector        = context.get("sector", "")
        requisitos    = context.get("requisitos", [])
        n             = context.get("n_preguntas") or _N_PREGUNTAS.get(profundidad, 5)
        prompt_custom = context.get("prompt_custom", "")

        try:
            preguntas = self._generar_con_ia(puesto, profundidad, canal, sector, requisitos, n, prompt_custom)
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

        # Persistir en Supabase
        payload = {
            "empresa_id":  empresa_id,
            "puesto":      puesto,
            "profundidad": profundidad,
            "canal":       canal,
            "preguntas":   preguntas,
        }
        if vacante_id:
            payload["vacante_id"] = vacante_id

        saved = db.rest_insert("cuestionarios", payload)
        cuestionario_id = None
        if saved.get("ok"):
            rows = saved.get("data") or []
            row = rows[0] if isinstance(rows, list) and rows else rows
            cuestionario_id = row.get("id") if isinstance(row, dict) else None

        return {
            "ok": True,
            "message": f"{len(preguntas)} preguntas generadas y guardadas ({profundidad})",
            "data": {
                "cuestionario_id": cuestionario_id,
                "puesto":          puesto,
                "profundidad":     profundidad,
                "canal":           canal,
                "preguntas":       preguntas,
                "generado_ahora":  True,
            },
        }

    # --- helpers ---

    def _buscar_existente(self, db: SupabaseClient, vacante_id: str) -> dict:
        result = db.rest_select(
            "cuestionarios",
            filters={"vacante_id": vacante_id},
            select="id,puesto,profundidad,canal,preguntas",
            limit=1,
        )
        if not result.get("ok"):
            return result
        rows = result.get("data") or []
        return {"ok": True, "data": rows[0] if rows else None}

    def _generar_con_ia(
        self,
        puesto: str,
        profundidad: str,
        canal: str,
        sector: str,
        requisitos: list,
        n: int,
        prompt_custom: str,
    ) -> list:
        system = (
            "Eres un especialista en reclutamiento. Generas cuestionarios conversacionales "
            "para filtrar candidatos por canal de mensajeria. "
            "Las preguntas deben ser cortas, claras y directas. "
            "Responde siempre en JSON valido sin bloques de codigo."
        )
        req_txt    = "\n".join(f"- {r}" for r in requisitos) if requisitos else ""
        canal_note = "Preguntas muy cortas, aptas para chat." if canal in ("telegram", "whatsapp", "instagram") else ""
        custom_note = f"\nInstrucciones adicionales: {prompt_custom}" if prompt_custom else ""

        prompt = (
            f"Genera un cuestionario de {n} preguntas para el puesto: {puesto}\n"
            f"{f'Sector: {sector}' if sector else ''}\n"
            f"{f'Requisitos clave:{chr(10)}{req_txt}' if req_txt else ''}\n"
            f"Profundidad: {profundidad}\n"
            f"{canal_note}{custom_note}\n\n"
            "Las preguntas deben cubrir: datos de contacto, disponibilidad, experiencia, "
            "ubicacion y requisitos tecnicos del puesto.\n\n"
            "Devuelve unicamente este JSON:\n"
            '{"preguntas": ["pregunta 1", "pregunta 2", ...]}'
        )

        raw  = self._call_anthropic(prompt, system)
        data = json.loads(self._strip_code_block(raw))
        preguntas = data.get("preguntas", [])
        if not preguntas or not isinstance(preguntas, list):
            raise ValueError(f"IA no devolvio lista de preguntas: {raw}")
        return preguntas

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
