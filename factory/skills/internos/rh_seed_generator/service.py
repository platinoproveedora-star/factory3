"""Service for rh_seed_generator - batch test data generation using AI."""

from __future__ import annotations

import json
import os
import urllib.request
from datetime import datetime

from factory.engine import SupabaseClient

_MAX_VACANTES    = 5
_MAX_CANDIDATOS  = 20


class RhSeedGeneratorService:

    def ejecutar(self, context: dict) -> dict:
        empresa_id = context.get("empresa_id", "").strip()
        if not empresa_id:
            return {"ok": False, "error": "empresa_id es requerido"}

        # Forzar prefijo seed_ para aislar de datos reales
        if not empresa_id.startswith("seed_"):
            empresa_id = f"seed_{empresa_id}"

        n_vacantes   = min(int(context.get("n_vacantes", 1)), _MAX_VACANTES)
        n_candidatos = min(int(context.get("n_candidatos_por_vacante", 5)), _MAX_CANDIDATOS)
        profundidad  = context.get("profundidad", "simple")
        puestos      = context.get("puestos", [])
        sectores     = context.get("sectores", ["logistica", "retail", "manufactura", "servicios"])
        seed_label   = context.get("seed_label") or f"seed_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        if context.get("dry_run", True):
            return {
                "ok": True,
                "message": "dry_run: nada insertado",
                "data": {
                    "seed_label":  seed_label,
                    "empresa_id":  empresa_id,
                    "n_vacantes":  n_vacantes,
                    "n_candidatos_por_vacante": n_candidatos,
                },
            }

        db      = SupabaseClient(context)
        resumen = {"vacantes": 0, "cuestionarios": 0, "candidatos": 0, "scores": 0, "pipeline": 0}
        errores = []

        for i in range(n_vacantes):
            puesto  = puestos[i] if i < len(puestos) else None
            sector  = sectores[i % len(sectores)]

            # Llamada 1: generar vacante + cuestionario
            vacante_data = self._generar_vacante(puesto, sector, profundidad)
            if not vacante_data:
                errores.append(f"vacante {i+1}: fallo generacion IA")
                continue

            # Insertar vacante
            v_row = db.rest_insert("vacantes", {
                "empresa_id":  empresa_id,
                "titulo":      vacante_data["titulo"],
                "descripcion": vacante_data["descripcion"],
                "requisitos":  vacante_data["requisitos"],
                "canal":       "telegram",
                "estado":      "activa",
            })
            if not v_row.get("ok"):
                errores.append(f"vacante {i+1}: {v_row.get('error')}")
                continue
            vacante_id = (v_row["data"][0] if isinstance(v_row["data"], list) else v_row["data"])["id"]
            self._track(db, seed_label, empresa_id, "vacantes", vacante_id)
            resumen["vacantes"] += 1

            # Insertar cuestionario
            preguntas = vacante_data.get("preguntas", [])
            q_row = db.rest_insert("cuestionarios", {
                "empresa_id":  empresa_id,
                "vacante_id":  vacante_id,
                "puesto":      vacante_data["titulo"],
                "profundidad": profundidad,
                "canal":       "telegram",
                "preguntas":   preguntas,
            })
            if q_row.get("ok"):
                q_id = (q_row["data"][0] if isinstance(q_row["data"], list) else q_row["data"])["id"]
                self._track(db, seed_label, empresa_id, "cuestionarios", q_id)
                resumen["cuestionarios"] += 1

            # Llamada 2: generar todos los candidatos en batch
            candidatos_batch = self._generar_candidatos(
                vacante_data["titulo"], vacante_data["descripcion"],
                preguntas, vacante_data.get("requisitos", {}), n_candidatos,
            )
            if not candidatos_batch:
                errores.append(f"vacante {i+1}: fallo generacion candidatos")
                continue

            for cand in candidatos_batch:
                # Insertar candidato
                c_row = db.rest_insert("candidatos", {
                    "vacante_id":   vacante_id,
                    "nombre":       cand.get("nombre"),
                    "telefono":     cand.get("telefono"),
                    "email":        cand.get("email"),
                    "canal":        "telegram",
                    "canal_user_id": cand.get("canal_user_id", f"test_{os.urandom(4).hex()}"),
                    "estado":       cand.get("etapa", "nuevo"),
                })
                if not c_row.get("ok"):
                    continue
                cand_id = (c_row["data"][0] if isinstance(c_row["data"], list) else c_row["data"])["id"]
                self._track(db, seed_label, empresa_id, "candidatos", cand_id)
                resumen["candidatos"] += 1

                # Insertar conversacion (finalizada)
                conv_row = db.rest_insert("conversaciones", {
                    "candidato_id":    cand_id,
                    "vacante_id":      vacante_id,
                    "canal":           "telegram",
                    "estado":          "finalizado",
                    "cuestionario_paso": len(preguntas),
                })
                if conv_row.get("ok"):
                    conv_id = (conv_row["data"][0] if isinstance(conv_row["data"], list) else conv_row["data"])["id"]
                    self._track(db, seed_label, empresa_id, "conversaciones", conv_id)

                # Insertar respuestas
                for idx, (preg, resp) in enumerate(zip(preguntas, cand.get("respuestas", []))):
                    r_row = db.rest_insert("respuestas", {
                        "candidato_id": cand_id,
                        "vacante_id":   vacante_id,
                        "pregunta":     preg,
                        "respuesta":    resp,
                        "orden":        idx,
                    })
                    if r_row.get("ok"):
                        r_id = (r_row["data"][0] if isinstance(r_row["data"], list) else r_row["data"])["id"]
                        self._track(db, seed_label, empresa_id, "respuestas", r_id)

                # Insertar score
                score_val = cand.get("score", 50)
                s_row = db.rest_insert("scores", {
                    "candidato_id":  cand_id,
                    "vacante_id":    vacante_id,
                    "score_total":   score_val,
                    "pasa_knockout": cand.get("pasa_knockout", score_val >= 60),
                    "detalle":       {"resumen": cand.get("resumen_score", "generado por seed")},
                })
                if s_row.get("ok"):
                    s_id = (s_row["data"][0] if isinstance(s_row["data"], list) else s_row["data"])["id"]
                    self._track(db, seed_label, empresa_id, "scores", s_id)
                    resumen["scores"] += 1

                # Insertar pipeline
                etapa = cand.get("etapa", "apto")
                p_row = db.rest_insert("pipeline", {
                    "candidato_id": cand_id,
                    "vacante_id":   vacante_id,
                    "etapa":        etapa,
                    "notas":        f"seed generado — score {score_val}",
                })
                if p_row.get("ok"):
                    p_id = (p_row["data"][0] if isinstance(p_row["data"], list) else p_row["data"])["id"]
                    self._track(db, seed_label, empresa_id, "pipeline", p_id)
                    resumen["pipeline"] += 1

                # Evento historial
                e_row = db.rest_insert("eventos_historial", {
                    "candidato_id": cand_id,
                    "tipo_evento":  "pipeline_cambiado",
                    "datos":        {"etapa_nueva": etapa, "etapa_anterior": None, "seed": True},
                })
                if e_row.get("ok"):
                    e_id = (e_row["data"][0] if isinstance(e_row["data"], list) else e_row["data"])["id"]
                    self._track(db, seed_label, empresa_id, "eventos_historial", e_id)

        return {
            "ok": True,
            "message": f"seed '{seed_label}' generado",
            "data": {
                "seed_label": seed_label,
                "empresa_id": empresa_id,
                "resumen":    resumen,
                "errores":    errores,
            },
        }

    # --- IA ---

    def _generar_vacante(self, puesto: str | None, sector: str, profundidad: str) -> dict | None:
        n_preguntas = {"simple": 5, "medio": 10, "robusto": 20}.get(profundidad, 5)
        puesto_txt  = f'El puesto es: "{puesto}".' if puesto else f"Inventa un puesto realista del sector {sector}."
        prompt = (
            f"{puesto_txt}\n"
            f"Sector: {sector}\n\n"
            f"Genera en JSON:\n"
            '{"titulo": "...", "descripcion": "...", '
            '"requisitos": {"reglas_knockout": [{"campo": "...", "debe_contener": "..."}], '
            '"criterios_scoring": ["criterio 1", "criterio 2"]}, '
            f'"preguntas": ["pregunta 1", ..., "pregunta {n_preguntas}"]'
            "}\n\n"
            "Las preguntas deben cubrir nombre, telefono, disponibilidad, experiencia y requisito tecnico clave."
        )
        system = "Eres experto en RH. Generas datos realistas para pruebas de software. Solo JSON valido, sin bloques de codigo."
        try:
            raw  = self._call_anthropic(prompt, system, max_tokens=1024)
            return json.loads(self._strip(raw))
        except Exception:
            return None

    def _generar_candidatos(self, titulo: str, descripcion: str, preguntas: list, requisitos: dict, n: int) -> list:
        pregs_txt = "\n".join(f"{i+1}. {p}" for i, p in enumerate(preguntas))
        prompt = (
            f"Vacante: {titulo}\n{descripcion}\n\n"
            f"Cuestionario:\n{pregs_txt}\n\n"
            f"Genera {n} candidatos diversos y realistas. Variedad obligatoria:\n"
            "- Algunos pasan knockout y tienen score alto (70-95)\n"
            "- Algunos fallan knockout (score 0-40, pasa_knockout: false)\n"
            "- Algunos score medio (41-69)\n"
            "- Nombres, telefonos, ubicaciones y respuestas diferentes entre si\n\n"
            "Devuelve JSON:\n"
            '{"candidatos": [{"nombre": "...", "telefono": "...", "email": "...", '
            '"canal_user_id": "tg_XXXXX", '
            '"respuestas": ["resp1", "resp2", ...], '
            '"score": N, "pasa_knockout": bool, '
            '"etapa": "apto|no_apto|listo_entrevista|rechazado", '
            '"resumen_score": "..."}]}'
        )
        system = "Eres experto en RH. Generas candidatos ficticios realistas para pruebas. Solo JSON valido, sin bloques de codigo."
        try:
            raw  = self._call_anthropic(prompt, system, max_tokens=4096)
            data = json.loads(self._strip(raw))
            return data.get("candidatos", [])
        except Exception:
            return []

    def _strip(self, text: str) -> str:
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1]
            if text.endswith("```"):
                text = text[:-3]
        return text.strip()

    def _call_anthropic(self, prompt: str, system: str, max_tokens: int = 1024) -> str:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY no configurada")
        payload = {
            "model":      "claude-haiku-4-5-20251001",
            "max_tokens": max_tokens,
            "system":     system,
            "messages":   [{"role": "user", "content": prompt}],
        }
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "content-type":    "application/json",
                "x-api-key":       api_key,
                "anthropic-version": "2023-06-01",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
        parts = [item.get("text", "") for item in result.get("content", []) if item.get("type") == "text"]
        return "\n".join(p for p in parts if p).strip()

    # --- supabase helpers ---

    def _track(self, db: SupabaseClient, seed_label: str, empresa_id: str, tabla: str, registro_id: str) -> None:
        db.rest_insert("test_seeds", {
            "seed_label":   seed_label,
            "empresa_id":   empresa_id,
            "tabla":        tabla,
            "registro_id":  registro_id,
        })
