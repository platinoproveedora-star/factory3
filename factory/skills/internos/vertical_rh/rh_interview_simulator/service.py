"""Simula un candidato respondiendo una entrevista completa via webhook."""
from __future__ import annotations

import json
import os
import random
import time
import urllib.request
from factory.engine import SupabaseClient

_EMPRESA_ID = os.getenv("RH_EMPRESA_ID", "rh_empresa_1")
_API_URL    = os.getenv("FACTORY_API_URL", "http://localhost:8000")
_BOT_NAME   = os.getenv("INTERVIEW_BOT_NAME", "factory3_admin")


class RhInterviewSimulatorService:

    def ejecutar(self, context: dict) -> dict:
        vacante_id = context.get("vacante_id", "").strip()
        delay      = float(context.get("delay_seconds", 1.5))
        dry_run    = context.get("dry_run", False)

        db = SupabaseClient(context)

        # Obtener vacante
        if vacante_id:
            v_r = db.rest_select("vacantes", filters={"id": vacante_id}, select="*", limit=1)
        else:
            v_r = db.rest_select("vacantes", filters={"estado": "eq.activa", "tipo": "eq.real"},
                                 select="*", limit=50)
        vacantes = (v_r.get("data") or []) if v_r.get("ok") else []
        if not vacantes:
            return {"ok": False, "error": "No hay vacantes activas disponibles"}

        vacante = random.choice(vacantes) if not vacante_id else vacantes[0]
        v_id    = vacante["id"]
        titulo  = vacante.get("titulo", "?")
        folio   = vacante.get("folio", "?")

        # Obtener cuestionario
        q_r = db.rest_select("cuestionarios", filters={"vacante_id": v_id},
                              select="preguntas", limit=1)
        q_rows = (q_r.get("data") or []) if q_r.get("ok") else []
        preguntas = q_rows[0].get("preguntas", []) if q_rows else []
        if not preguntas:
            return {"ok": False, "error": f"No hay cuestionario para vacante {folio}"}

        # Generar perfil del candidato con IA
        perfil = self._generar_perfil(titulo, preguntas)
        if not perfil:
            return {"ok": False, "error": "Fallo generación de perfil con IA"}

        if dry_run:
            return {"ok": True, "data": {"vacante": folio, "titulo": titulo,
                                          "candidato": perfil.get("nombre"), "dry_run": True}}

        # Simular chat_id único
        chat_id = random.randint(9000000, 9999999)

        # Enviar /start al bot
        self._webhook(f"/start", chat_id)
        time.sleep(delay)

        # Entrar a modo rh1
        self._webhook("/rh1", chat_id)
        time.sleep(delay)

        # El bot preguntará la primera pregunta — simulamos respuestas
        respuestas = perfil.get("respuestas", [])
        for i, respuesta in enumerate(respuestas):
            self._webhook(respuesta, chat_id)
            time.sleep(delay)

        return {
            "ok": True,
            "data": {
                "vacante_folio": folio,
                "vacante_titulo": titulo,
                "candidato_nombre": perfil.get("nombre"),
                "chat_id_simulado": chat_id,
                "respuestas_enviadas": len(respuestas),
                "response": (
                    f"✓ Simulación completada\n"
                    f"Vacante: <b>{folio}</b> {titulo}\n"
                    f"Candidato: {perfil.get('nombre')}\n"
                    f"Respuestas enviadas: {len(respuestas)}"
                ),
            },
        }

    def _generar_perfil(self, titulo: str, preguntas: list) -> dict | None:
        pregs_txt = "\n".join(f"{i+1}. {p}" for i, p in enumerate(preguntas))
        prompt = (
            f"Vacante: {titulo}\n\n"
            f"Cuestionario:\n{pregs_txt}\n\n"
            "Genera un candidato realista que SÍ cumple los requisitos (perfil positivo).\n"
            "JSON: {\"nombre\":\"...\",\"telefono\":\"55XXXXXXXX\","
            "\"respuestas\":[\"resp1\",\"resp2\",...]} "
            "— una respuesta por pregunta, en orden, natural y conversacional."
        )
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return None
        payload = {
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 1024,
            "system": "Eres un candidato real respondiendo una entrevista de trabajo. Solo JSON válido.",
            "messages": [{"role": "user", "content": prompt}],
        }
        try:
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=json.dumps(payload).encode(),
                headers={"content-type": "application/json",
                         "x-api-key": api_key, "anthropic-version": "2023-06-01"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=60) as r:
                result = json.loads(r.read())
            raw = result["content"][0]["text"].strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[-1]
                if raw.endswith("```"):
                    raw = raw[:-3]
            return json.loads(raw.strip())
        except Exception:
            return None

    def _webhook(self, text: str, chat_id: int) -> dict:
        update = {
            "message": {
                "message_id": random.randint(1000, 9999),
                "from": {"id": chat_id, "first_name": "Candidato", "is_bot": False},
                "chat": {"id": chat_id, "type": "private"},
                "text": text,
            }
        }
        url = f"{_API_URL}/webhook/{_BOT_NAME}"
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(update).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read())
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
