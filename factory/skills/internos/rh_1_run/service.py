"""Master orchestrator for rh_1 mode — all RH commands + candidate pipeline."""

from __future__ import annotations

import os
from pathlib import Path

from factory.engine import SkillLoader, SkillRunner, SupabaseClient

_BASE = Path(__file__).parent.parent.parent.parent.parent  # factory3 root

_AYUDA = (
    "Modo RH-1 activo.\n\n"
    "Comandos:\n"
    "/vacantes — listar vacantes activas\n"
    "/vacante <ID> — seleccionar vacante activa\n"
    "/ranking — top candidatos (vacante activa)\n"
    "/reporte — resumen pipeline (vacante activa)\n"
    "/seed <N> — generar N vacantes de prueba con candidatos\n"
    "/limpiar <LABEL> — borrar datos del seed\n"
    "/salir — salir del modo RH\n\n"
    "Con vacante activa, escribe cualquier texto para simular un candidato."
)


class Rh1RunService:

    def __init__(self):
        self._runner = None

    def _get_runner(self):
        if self._runner is None:
            loader = SkillLoader(
                internal_root=_BASE / "factory" / "skills" / "internos",
                external_root=_BASE / "factory" / "skills" / "externos",
            )
            self._runner = SkillRunner(loader)
        return self._runner

    def ejecutar(self, context: dict) -> dict:
        update    = context.get("update", {})
        state     = context.get("state", {})
        message   = update.get("message", {})
        text      = (message.get("text") or "").strip()

        empresa_id = os.getenv("RH_EMPRESA_ID", "rh_empresa_1")
        vacante_id = state.get("rh_vacante_id", "")

        parts = text.split(None, 1)
        cmd   = parts[0].lower() if parts else ""
        arg   = parts[1].strip() if len(parts) > 1 else ""

        if cmd in ("/ayuda", "/help"):
            return self._ok(_AYUDA, state)

        if cmd == "/vacantes":
            return self._cmd_vacantes(empresa_id, state)

        if cmd == "/vacante":
            return self._cmd_set_vacante(empresa_id, arg, state)

        if cmd == "/ranking":
            if not vacante_id:
                return self._ok("Primero selecciona una vacante con /vacante <ID>.", state)
            return self._cmd_ranking(vacante_id, state)

        if cmd == "/reporte":
            if not vacante_id:
                return self._ok("Primero selecciona una vacante con /vacante <ID>.", state)
            return self._cmd_reporte(empresa_id, vacante_id, state)

        if cmd == "/seed":
            try:
                n = max(1, int(arg)) if arg else 1
            except ValueError:
                n = 1
            return self._cmd_seed(empresa_id, n, state)

        if cmd == "/limpiar":
            return self._cmd_limpiar(empresa_id, arg, state)

        # Normal text → candidate pipeline
        if not vacante_id:
            return self._ok(
                "No hay vacante activa.\nUsa /vacantes para listarlas o /vacante <ID> para seleccionar una.",
                state,
            )
        return self._candidato_pipeline(update, vacante_id, empresa_id, state)

    # -------------------------------------------------------------------------
    # Commands
    # -------------------------------------------------------------------------

    def _cmd_vacantes(self, empresa_id: str, state: dict) -> dict:
        db = SupabaseClient({})
        r = db.rest_select(
            "vacantes",
            filters={"empresa_id": empresa_id, "estado": "activa"},
            select="id,titulo",
        )
        rows = (r.get("data") or []) if r.get("ok") else []
        if not rows:
            rows2 = db.rest_select("vacantes", filters={"empresa_id": empresa_id}, select="id,titulo")
            rows = (rows2.get("data") or []) if rows2.get("ok") else []
        if not rows:
            return self._ok(
                f"No hay vacantes para empresa '{empresa_id}'.\nUsa /seed 1 para generar datos de prueba.",
                state,
            )
        lines = [f"Vacantes ({len(rows)}):"]
        for v in rows[:10]:
            lines.append(f"• {v.get('titulo', '?')}")
            lines.append(f"  /vacante {v['id']}")
        return self._ok("\n".join(lines), state)

    def _cmd_set_vacante(self, empresa_id: str, vacante_id: str, state: dict) -> dict:
        if not vacante_id:
            return self._cmd_vacantes(empresa_id, state)
        db = SupabaseClient({})
        r = db.rest_select("vacantes", filters={"id": vacante_id}, select="id,titulo", limit=1)
        rows = (r.get("data") or []) if r.get("ok") else []
        if not rows:
            return self._ok(f"Vacante no encontrada: {vacante_id[:8]}...", state)
        titulo = rows[0].get("titulo", "?")
        new_state = {**state, "rh_vacante_id": vacante_id}
        return self._ok(f"Vacante activa: {titulo}\n\nEscribe cualquier texto para simular un candidato.", new_state)

    def _cmd_ranking(self, vacante_id: str, state: dict) -> dict:
        r = self._get_runner().run(
            "rh_candidate_ranking",
            {"vacante_id": vacante_id, "limite": 10},
            source="internos",
        )
        if not r.get("ok"):
            return self._ok(f"Error obteniendo ranking: {r.get('error')}", state)
        ranking = (r.get("data") or {}).get("ranking") or []
        total   = (r.get("data") or {}).get("total", 0)
        if not ranking:
            return self._ok("Sin candidatos evaluados aún.", state)
        lines = [f"Top candidatos ({total} total):"]
        for c in ranking:
            score  = c.get("score_total")
            nombre = c.get("nombre", "Sin nombre")
            estado = c.get("estado", "")
            ko     = "✓" if c.get("pasa_knockout") else "✗"
            score_txt = str(score) if score is not None else "—"
            lines.append(f"{c['posicion']}. {nombre} | score {score_txt} | KO {ko} | {estado}")
        return self._ok("\n".join(lines), state)

    def _cmd_reporte(self, empresa_id: str, vacante_id: str, state: dict) -> dict:
        r = self._get_runner().run(
            "rh_report_generator",
            {"tipo": "pipeline", "vacante_id": vacante_id, "empresa_id": empresa_id},
            source="internos",
        )
        if not r.get("ok"):
            return self._ok(f"Error generando reporte: {r.get('error')}", state)
        d = r.get("data") or {}
        lines = [
            f"Reporte pipeline — {d.get('total', 0)} candidatos",
            "",
            "Por estado:",
        ]
        for estado, cnt in sorted((d.get("por_estado") or {}).items()):
            lines.append(f"  {estado}: {cnt}")
        lines.append("")
        lines.append("Por canal:")
        for canal, cnt in sorted((d.get("por_canal") or {}).items()):
            lines.append(f"  {canal}: {cnt}")
        return self._ok("\n".join(lines), state)

    def _cmd_seed(self, empresa_id: str, n: int, state: dict) -> dict:
        raw_id = empresa_id.removeprefix("seed_")
        r = self._get_runner().run(
            "rh_seed_generator",
            {
                "empresa_id":                  raw_id,
                "n_vacantes":                  min(n, 3),
                "n_candidatos_por_vacante":    5,
                "profundidad":                 "simple",
                "dry_run":                     False,
            },
            source="internos",
        )
        if not r.get("ok"):
            return self._ok(f"Error generando seed: {r.get('error')}", state)
        d    = r.get("data") or {}
        res  = d.get("resumen") or {}
        errs = d.get("errores") or []
        label = d.get("seed_label", "?")
        msg = (
            f"Seed generado: {label}\n"
            f"Vacantes: {res.get('vacantes', 0)}\n"
            f"Candidatos: {res.get('candidatos', 0)}\n"
            f"Scores: {res.get('scores', 0)}"
        )
        if errs:
            msg += f"\nErrores: {len(errs)}"
        msg += f"\n\nPara limpiar: /limpiar {label}"
        return self._ok(msg, state)

    def _cmd_limpiar(self, empresa_id: str, label: str, state: dict) -> dict:
        if not label:
            return self._ok("Uso: /limpiar <seed_label>  (ej: /limpiar seed_20250504_120000)", state)
        raw_id = empresa_id.removeprefix("seed_")
        r = self._get_runner().run(
            "rh_seed_cleaner",
            {"seed_label": label, "empresa_id": raw_id, "dry_run": False},
            source="internos",
        )
        if not r.get("ok"):
            return self._ok(f"Error al limpiar: {r.get('error')}", state)
        d     = r.get("data") or {}
        total = sum((d.get("borrados") or {}).values())
        return self._ok(f"Seed '{label}' eliminado — {total} registros borrados.", state)

    # -------------------------------------------------------------------------
    # Candidate pipeline
    # -------------------------------------------------------------------------

    def _candidato_pipeline(self, update: dict, vacante_id: str, empresa_id: str, state: dict) -> dict:
        message       = update.get("message", {})
        text          = (message.get("text") or "").strip()
        user_id       = str((message.get("from") or {}).get("id", ""))

        # 1. Route
        route_r = self._get_runner().run(
            "bot_inbox_router",
            {
                "canal":       "telegram",
                "user_id":     user_id,
                "empresa_id":  empresa_id,
                "vacante_id":  vacante_id,
            },
            source="internos",
        )
        if not route_r.get("ok"):
            return self._ok(f"Error de enrutamiento: {route_r.get('error')}", state)

        route           = route_r.get("data") or {}
        candidate_id    = route.get("candidate_id")
        conversation_id = route.get("conversation_id")

        if not candidate_id or not conversation_id:
            return self._ok("No se pudo identificar al candidato.", state)

        if route.get("requiere_humano"):
            return self._ok(
                "Tu perfil ya fue completado. El equipo de RH te contactará pronto.", state
            )

        # 2. Get preguntas
        preguntas = self._get_preguntas(vacante_id)
        if not preguntas:
            return self._ok(
                "Esta vacante no tiene cuestionario configurado todavía.\n"
                "Genera datos de prueba con /seed 1 primero.",
                state,
            )

        # 3. Form capture
        form_r = self._get_runner().run(
            "bot_form_capture",
            {
                "conversation_id": conversation_id,
                "candidato_id":    candidate_id,
                "vacante_id":      vacante_id,
                "preguntas":       preguntas,
                "message_text":    text,
            },
            source="internos",
        )
        if not form_r.get("ok"):
            return self._ok(f"Error en formulario: {form_r.get('error')}", state)

        form = form_r.get("data") or {}
        if form.get("completado"):
            return self._ok(
                "¡Gracias por completar el formulario!\n"
                "Tu perfil ha sido registrado y será evaluado por el equipo de RH.\n\n"
                "Usa /ranking para ver el estado de los candidatos.",
                state,
            )

        pregunta = form.get("pregunta_siguiente")
        if pregunta:
            paso  = form.get("paso_actual", 1)
            total = form.get("total_pasos", len(preguntas))
            return self._ok(f"[{paso}/{total}] {pregunta}", state)

        return self._ok("Procesando tu respuesta...", state)

    def _get_preguntas(self, vacante_id: str) -> list:
        db = SupabaseClient({})
        r  = db.rest_select(
            "cuestionarios",
            filters={"vacante_id": vacante_id},
            select="preguntas",
            limit=1,
        )
        if not r.get("ok"):
            return []
        rows = r.get("data") or []
        if not rows:
            return []
        preguntas = rows[0].get("preguntas")
        return preguntas if isinstance(preguntas, list) else []

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _ok(self, response: str, state: dict) -> dict:
        return {"ok": True, "data": {"response": response, "state": state}}
