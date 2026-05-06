"""Service for rh_candidate_scoring - AI scoring of candidate profile."""

from __future__ import annotations

import json
import os
import urllib.request

from factory.engine import SupabaseClient


class RhCandidateScoringService:

    def ejecutar(self, context: dict) -> dict:
        candidato_id = context.get("candidato_id", "").strip()
        vacante_id   = context.get("vacante_id", "").strip()
        perfil       = context.get("perfil")

        if not candidato_id:
            return {"ok": False, "error": "candidato_id es requerido"}
        if not vacante_id:
            return {"ok": False, "error": "vacante_id es requerido"}
        if not perfil or not isinstance(perfil, dict):
            return {"ok": False, "error": "perfil es requerido y debe ser un diccionario"}

        vacante_titulo   = context.get("vacante_titulo", "vacante")
        vacante_desc     = context.get("vacante_descripcion", "")
        criterios        = context.get("criterios_scoring", [])
        pasa_knockout    = context.get("pasa_knockout", True)

        if context.get("dry_run", False):
            return {"ok": True, "message": "dry_run", "data": {"candidato_id": candidato_id, "perfil": perfil}}

        resultado = self._score_con_ia(perfil, vacante_titulo, vacante_desc, criterios)
        if not resultado.get("ok"):
            return resultado

        score_data = resultado["data"]

        db = SupabaseClient(context)
        saved = db.rest_insert("scores", {
            "candidato_id": candidato_id,
            "vacante_id":   vacante_id,
            "score_total":  score_data["score_total"],
            "pasa_knockout": pasa_knockout,
            "detalle":      score_data.get("detalle"),
        })
        if not saved.get("ok"):
            return saved

        rows = saved.get("data") or []
        score_record = rows[0] if isinstance(rows, list) and rows else rows

        return {
            "ok": True,
            "message": f"score: {score_data['score_total']}/100",
            "data": {
                "candidato_id":  candidato_id,
                "score_total":   score_data["score_total"],
                "pasa_knockout": pasa_knockout,
                "detalle":       score_data.get("detalle"),
                "score_id":      score_record.get("id") if isinstance(score_record, dict) else None,
            },
        }

    def _score_con_ia(self, perfil: dict, titulo: str, descripcion: str, criterios: list) -> dict:
        criterios_txt = ""
        if criterios:
            criterios_txt = "\nCriterios de evaluacion:\n" + "\n".join(f"- {c}" for c in criterios)

        system = (
            "Eres un evaluador de candidatos para recursos humanos. "
            "Evalua objetivamente el perfil del candidato segun la vacante. "
            "Responde SIEMPRE en JSON valido, sin texto adicional ni bloques de codigo."
        )

        prompt = (
            f"Vacante: {titulo}\n"
            f"{('Descripcion: ' + descripcion) if descripcion else ''}"
            f"{criterios_txt}\n\n"
            f"Perfil del candidato:\n{json.dumps(perfil, ensure_ascii=False, indent=2)}\n\n"
            "Puntua al candidato del 0 al 100 considerando:\n"
            "- Experiencia relevante (30 pts)\n"
            "- Disponibilidad adecuada (25 pts)\n"
            "- Ubicacion / acceso (20 pts)\n"
            "- Documentacion y requisitos tecnicos (25 pts)\n\n"
            "Devuelve unicamente este JSON:\n"
            '{"score_total": N, "detalle": {"experiencia": N, "disponibilidad": N, "ubicacion": N, "requisitos": N, "resumen": "..."}}'
        )

        try:
            raw = self._call_anthropic(prompt, system)
            cleaned = self._strip_code_block(raw)
            data = json.loads(cleaned)
            if "score_total" not in data:
                return {"ok": False, "error": f"respuesta inesperada de IA: {raw}"}
            return {"ok": True, "data": data}
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
            "max_tokens": 512,
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
