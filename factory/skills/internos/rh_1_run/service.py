"""Master orchestrator rh1 — all commands independent, inline keyboard buttons."""

from __future__ import annotations

import os
from pathlib import Path

from factory.engine import SkillLoader, SkillRunner, SupabaseClient

_BASE       = Path(__file__).parent.parent.parent.parent.parent  # factory3 root
_EMPRESA_ID = os.getenv("RH_EMPRESA_ID", "rh_empresa_1")
_DASHBOARD  = os.getenv("DASHBOARD_URL", "https://factory3-dashboard.onrender.com")

_ETAPAS = ["nuevo", "apto", "no_apto", "listo_entrevista", "entrevistado", "rechazado", "contratado"]

_AYUDA = (
    "<b>Modo RH activo</b>\n\n"
    "<b>Vacantes</b>\n"
    "/vacantes — listar vacantes\n"
    "/ranking N — top candidatos de vacante N\n"
    "/reporte N — resumen pipeline de vacante N\n"
    "/candidatos N — candidatos de vacante N\n"
    "/candidato FOLIO — detalle de un candidato\n"
    "/mover FOLIO etapa — mover candidato en pipeline\n\n"
    "<b>Seeds (pruebas)</b>\n"
    "/seed N — crear N vacantes con 5 candidatos\n"
    "/seedc N FOLIO — agregar N candidatos a vacante\n"
    "/seeds — listar seeds generados\n"
    "/limpiar LABEL — borrar seed completo\n\n"
    "<b>General</b>\n"
    "/status — resumen general\n"
    "/dashboard — abrir dashboard\n"
    "/salir — salir del modo RH"
)


class Rh1RunService:

    def __init__(self):
        self._runner: SkillRunner | None = None

    def _get_runner(self) -> SkillRunner:
        if self._runner is None:
            ext = _BASE / "factory" / "skills" / "externos"
            ext.mkdir(parents=True, exist_ok=True)
            loader = SkillLoader(
                internal_root=_BASE / "factory" / "skills" / "internos",
                external_root=ext,
            )
            self._runner = SkillRunner(loader)
        return self._runner

    def ejecutar(self, context: dict) -> dict:
        update  = context.get("update", {})
        state   = context.get("state", {})
        message = update.get("message", {})
        text    = (message.get("text") or "").strip()

        parts = text.split(None, 2)
        cmd   = parts[0].lower() if parts else ""
        arg1  = parts[1].strip() if len(parts) > 1 else ""
        arg2  = parts[2].strip() if len(parts) > 2 else ""

        if cmd in ("/ayuda", "/help"):
            return self._ok(_AYUDA, state, reply_markup=self._ayuda_buttons())

        if cmd == "/vacantes":
            return self._cmd_vacantes(state)

        if cmd == "/ranking":
            return self._cmd_ranking(arg1, state)

        if cmd == "/reporte":
            return self._cmd_reporte(arg1, state)

        if cmd == "/candidatos":
            return self._cmd_candidatos(arg1, state)

        if cmd == "/candidato":
            return self._cmd_candidato_detalle(arg1, state)

        if cmd == "/mover":
            return self._cmd_mover(arg1, arg2, state)

        if cmd == "/status":
            return self._cmd_status(state)

        if cmd == "/dashboard":
            return self._cmd_dashboard(state)

        if cmd == "/seed":
            return self._cmd_seed(arg1, update, state)

        if cmd == "/seedc":
            return self._cmd_seedc(arg1, arg2, state)

        if cmd == "/seeds":
            return self._cmd_seeds(state)

        if cmd == "/limpiar":
            return self._cmd_limpiar(arg1, state)

        # Candidate pipeline — normal text
        return self._candidato_pipeline(update, state)

    # -------------------------------------------------------------------------
    # Vacantes
    # -------------------------------------------------------------------------

    def _cmd_vacantes(self, state: dict) -> dict:
        db   = SupabaseClient({})
        rows = self._get_vacantes(db)
        if not rows:
            return self._ok(
                "No hay vacantes.\nUsa /seed 1 para generar datos de prueba.",
                state,
                reply_markup={"inline_keyboard": [[{"text": "Generar seed", "callback_data": "/seed 1"}]]}
            )
        lines = ["<b>Vacantes:</b>"]
        buttons = []
        for v in rows[:10]:
            folio  = v.get("folio", "?")
            titulo = v.get("titulo", "Sin título")
            tipo   = " [SEED]" if v.get("tipo") == "seed" else ""
            lines.append(f"<b>{folio}</b>{tipo} — {titulo}")
            buttons.append([{"text": f"{folio} — {titulo[:30]}", "callback_data": f"/ranking {folio}"}])
        buttons.append([{"text": "Status general", "callback_data": "/status"}])
        return self._ok("\n".join(lines), state, reply_markup={"inline_keyboard": buttons})

    def _cmd_ranking(self, arg: str, state: dict) -> dict:
        if not arg:
            return self._pedir_vacante("ranking", state)
        vacante = self._resolver_vacante(arg)
        if not vacante:
            return self._ok(f"Vacante '{arg}' no encontrada. Usa /vacantes para ver la lista.", state)
        r = self._get_runner().run(
            "rh_candidate_ranking",
            {"vacante_id": vacante["id"], "limite": 10},
            source="internos",
        )
        if not r.get("ok"):
            return self._ok(f"Error: {r.get('error')}", state)
        ranking = (r.get("data") or {}).get("ranking") or []
        total   = (r.get("data") or {}).get("total", 0)
        if not ranking:
            return self._ok(f"Sin candidatos evaluados en {vacante['folio']}.", state)
        lines   = [f"<b>Ranking {vacante['folio']} — {vacante.get('titulo','')}</b>\n<i>{total} candidatos</i>\n"]
        buttons = []
        for c in ranking:
            score  = c.get("score_total")
            nombre = c.get("nombre", "Sin nombre")
            ko     = "✓" if c.get("pasa_knockout") else "✗"
            s_txt  = str(score) if score is not None else "—"
            folio  = c.get("folio") or c.get("candidato_id", "")[:8]
            lines.append(f"{c['posicion']}. <b>{nombre}</b> | {s_txt}pts | KO {ko}")
            if folio:
                buttons.append([{"text": f"Ver {nombre[:20]}", "callback_data": f"/candidato {folio}"}])
        buttons.append([{"text": "Ver reporte", "callback_data": f"/reporte {vacante['folio']}"}])
        return self._ok("\n".join(lines), state, reply_markup={"inline_keyboard": buttons})

    def _cmd_reporte(self, arg: str, state: dict) -> dict:
        if not arg:
            return self._pedir_vacante("reporte", state)
        vacante = self._resolver_vacante(arg)
        if not vacante:
            return self._ok(f"Vacante '{arg}' no encontrada.", state)
        r = self._get_runner().run(
            "rh_report_generator",
            {"tipo": "pipeline", "vacante_id": vacante["id"], "empresa_id": _EMPRESA_ID},
            source="internos",
        )
        if not r.get("ok"):
            return self._ok(f"Error: {r.get('error')}", state)
        d     = r.get("data") or {}
        lines = [f"<b>Reporte {vacante['folio']} — {vacante.get('titulo','')}</b>",
                 f"Total candidatos: <b>{d.get('total', 0)}</b>\n",
                 "<b>Por estado:</b>"]
        for est, cnt in sorted((d.get("por_estado") or {}).items()):
            lines.append(f"  {est}: {cnt}")
        lines.append("\n<b>Por canal:</b>")
        for canal, cnt in sorted((d.get("por_canal") or {}).items()):
            lines.append(f"  {canal}: {cnt}")
        buttons = [[
            {"text": "Ver ranking", "callback_data": f"/ranking {vacante['folio']}"},
            {"text": "Ver candidatos", "callback_data": f"/candidatos {vacante['folio']}"},
        ]]
        return self._ok("\n".join(lines), state, reply_markup={"inline_keyboard": buttons})

    def _cmd_candidatos(self, arg: str, state: dict) -> dict:
        if not arg:
            return self._pedir_vacante("candidatos", state)
        vacante = self._resolver_vacante(arg)
        if not vacante:
            return self._ok(f"Vacante '{arg}' no encontrada.", state)
        db = SupabaseClient({})
        r  = db.rest_select(
            "candidatos",
            filters={"vacante_id": vacante["id"]},
            select="id,folio,nombre,estado,canal,created_at",
        )
        rows = (r.get("data") or []) if r.get("ok") else []
        if not rows:
            return self._ok(f"Sin candidatos en {vacante['folio']}.", state)
        lines   = [f"<b>Candidatos {vacante['folio']} ({len(rows)}):</b>\n"]
        buttons = []
        for c in rows[:15]:
            folio  = c.get("folio", "?")
            nombre = c.get("nombre") or "Sin nombre"
            estado = c.get("estado", "")
            lines.append(f"<b>{folio}</b> — {nombre} [{estado}]")
            buttons.append([{"text": f"{folio} — {nombre[:25]}", "callback_data": f"/candidato {folio}"}])
        return self._ok("\n".join(lines), state, reply_markup={"inline_keyboard": buttons})

    def _cmd_candidato_detalle(self, folio: str, state: dict) -> dict:
        if not folio:
            return self._ok("Uso: /candidato CAND-001", state)
        db  = SupabaseClient({})
        r   = db.rest_select("candidatos", filters={"folio": folio}, select="id,folio,nombre,telefono,email,estado,canal,vacante_id,created_at", limit=1)
        rows = (r.get("data") or []) if r.get("ok") else []
        if not rows:
            return self._ok(f"Candidato {folio} no encontrado.", state)
        c = rows[0]
        # Get score
        sr = db.rest_select("scores", filters={"candidato_id": c["id"]}, select="score_total,pasa_knockout,detalle", limit=1)
        score_row = ((sr.get("data") or [{}])[0]) if sr.get("ok") else {}
        # Get respuestas
        rr = db.rest_select("respuestas", filters={"candidato_id": c["id"]}, select="pregunta,respuesta,orden")
        respuestas = sorted((rr.get("data") or []), key=lambda x: x.get("orden", 0)) if rr.get("ok") else []

        lines = [
            f"<b>Candidato {c.get('folio')}</b>",
            f"Nombre: {c.get('nombre') or '—'}",
            f"Teléfono: {c.get('telefono') or '—'}",
            f"Email: {c.get('email') or '—'}",
            f"Estado: {c.get('estado') or '—'}",
            f"Canal: {c.get('canal') or '—'}",
        ]
        if score_row:
            ko = "✓ Pasa" if score_row.get("pasa_knockout") else "✗ No pasa"
            lines += [f"\n<b>Score:</b> {score_row.get('score_total', '—')}pts | KO: {ko}"]
            resumen = (score_row.get("detalle") or {}).get("resumen")
            if resumen:
                lines.append(f"<i>{resumen}</i>")
        if respuestas:
            lines.append("\n<b>Respuestas:</b>")
            for resp in respuestas[:5]:
                lines.append(f"<i>P: {resp.get('pregunta','')[:50]}</i>")
                lines.append(f"R: {resp.get('respuesta','')[:80]}")
        etapa_buttons = [
            [{"text": "✓ Apto", "callback_data": f"/mover {folio} apto"},
             {"text": "✗ No apto", "callback_data": f"/mover {folio} no_apto"}],
            [{"text": "Entrevista", "callback_data": f"/mover {folio} listo_entrevista"},
             {"text": "Rechazar", "callback_data": f"/mover {folio} rechazado"}],
        ]
        return self._ok("\n".join(lines), state, reply_markup={"inline_keyboard": etapa_buttons})

    def _cmd_mover(self, folio: str, etapa: str, state: dict) -> dict:
        if not folio or not etapa:
            return self._ok("Uso: /mover CAND-001 apto\nEtapas: " + ", ".join(_ETAPAS), state)
        etapa = etapa.lower()
        if etapa not in _ETAPAS:
            return self._ok(f"Etapa inválida. Válidas: {', '.join(_ETAPAS)}", state)
        db = SupabaseClient({})
        r  = db.rest_select("candidatos", filters={"folio": folio}, select="id,nombre,vacante_id", limit=1)
        rows = (r.get("data") or []) if r.get("ok") else []
        if not rows:
            return self._ok(f"Candidato {folio} no encontrado.", state)
        c = rows[0]
        db.rest_update("candidatos", values={"estado": etapa}, filters={"id": c["id"]})
        db.rest_insert("pipeline", {"candidato_id": c["id"], "vacante_id": c["vacante_id"], "etapa": etapa, "notas": "movido por manager"})
        db.rest_insert("eventos_historial", {"candidato_id": c["id"], "tipo_evento": "pipeline_cambiado", "datos": {"etapa_nueva": etapa}})
        nombre = c.get("nombre") or folio
        return self._ok(f"✓ {nombre} movido a <b>{etapa}</b>.", state,
                        reply_markup={"inline_keyboard": [[{"text": "Ver candidato", "callback_data": f"/candidato {folio}"}]]})

    # -------------------------------------------------------------------------
    # Status & Dashboard
    # -------------------------------------------------------------------------

    def _cmd_status(self, state: dict) -> dict:
        db = SupabaseClient({})
        vac  = db.rest_select("vacantes", filters={"tipo": "real"}, select="id")
        cand = db.rest_select("candidatos", select="id,estado")
        sc   = db.rest_select("scores", select="score_total")

        n_vac  = len((vac.get("data") or [])) if vac.get("ok") else 0
        cands  = (cand.get("data") or []) if cand.get("ok") else []
        scores = [(s.get("score_total") or 0) for s in (sc.get("data") or []) if sc.get("ok") and s.get("score_total")]

        n_cand  = len(cands)
        n_aptos = sum(1 for c in cands if c.get("estado") in {"apto", "listo_entrevista", "entrevistado", "contratado"})
        avg_sc  = round(sum(scores) / len(scores), 1) if scores else 0

        lines = [
            "<b>Status RH</b>",
            f"Vacantes activas: <b>{n_vac}</b>",
            f"Candidatos totales: <b>{n_cand}</b>",
            f"Aptos: <b>{n_aptos}</b>",
            f"Score promedio: <b>{avg_sc}</b>",
        ]
        buttons = [[
            {"text": "Vacantes", "callback_data": "/vacantes"},
            {"text": "Dashboard", "url": _DASHBOARD},
        ]]
        return self._ok("\n".join(lines), state, reply_markup={"inline_keyboard": buttons})

    def _cmd_dashboard(self, state: dict) -> dict:
        return self._ok(
            "Abre el dashboard para ver y gestionar todo:",
            state,
            reply_markup={"inline_keyboard": [[{"text": "Abrir Dashboard", "url": _DASHBOARD}]]}
        )

    # -------------------------------------------------------------------------
    # Seeds
    # -------------------------------------------------------------------------

    def _cmd_seed(self, arg: str, update: dict, state: dict) -> dict:
        try:
            n = max(1, int(arg)) if arg else 1
        except ValueError:
            n = 1
        n = min(n, 3)
        chat_id = (update.get("message") or {}).get("chat", {}).get("id")

        return {
            "ok": True,
            "data": {
                "response": f"Generando {n} vacante(s) con candidatos...\nTe aviso cuando esté listo.",
                "state": state,
                "background_task": {
                    "skill":   "rh_seed_generator",
                    "context": {
                        "empresa_id":               _EMPRESA_ID,
                        "n_vacantes":               n,
                        "n_candidatos_por_vacante":  5,
                        "profundidad":               "simple",
                        "dry_run":                   False,
                        "tipo":                      "seed",
                    },
                },
            },
        }

    def _cmd_seedc(self, arg1: str, arg2: str, state: dict) -> dict:
        try:
            n = max(1, int(arg1)) if arg1 else 5
        except ValueError:
            n = 5
        folio = arg2.upper() if arg2 else ""
        if not folio:
            return self._ok("Uso: /seedc N VAC-001\nEjemplo: /seedc 10 VAC-001", state)
        vacante = self._resolver_vacante(folio)
        if not vacante:
            return self._ok(f"Vacante '{folio}' no encontrada.", state)
        return {
            "ok": True,
            "data": {
                "response": f"Agregando {n} candidatos a {folio}...\nTe aviso cuando esté listo.",
                "state": state,
                "background_task": {
                    "skill":   "rh_seed_generator",
                    "context": {
                        "empresa_id":               _EMPRESA_ID,
                        "vacante_id_existente":      vacante["id"],
                        "vacante_titulo":            vacante.get("titulo", ""),
                        "n_vacantes":               0,
                        "n_candidatos_por_vacante":  n,
                        "profundidad":               "simple",
                        "dry_run":                   False,
                        "tipo":                      "seed",
                    },
                },
            },
        }

    def _cmd_seeds(self, state: dict) -> dict:
        db = SupabaseClient({})
        r  = db.rest_select("test_seeds", select="seed_label,tabla,created_at")
        rows = (r.get("data") or []) if r.get("ok") else []
        if not rows:
            return self._ok("No hay seeds generados.", state)
        conteo: dict[str, int] = {}
        for row in rows:
            lbl = row.get("seed_label", "?")
            conteo[lbl] = conteo.get(lbl, 0) + 1
        lines   = ["<b>Seeds generados:</b>"]
        buttons = []
        for lbl, cnt in sorted(conteo.items()):
            lines.append(f"• <code>{lbl}</code> — {cnt} registros")
            buttons.append([{"text": f"Limpiar {lbl}", "callback_data": f"/limpiar {lbl}"}])
        return self._ok("\n".join(lines), state, reply_markup={"inline_keyboard": buttons})

    def _cmd_limpiar(self, label: str, state: dict) -> dict:
        if not label:
            return self._ok("Uso: /limpiar seed_20250506_130000\nUsa /seeds para ver los labels.", state)
        r = self._get_runner().run(
            "rh_seed_cleaner",
            {"seed_label": label, "empresa_id": _EMPRESA_ID, "dry_run": False},
            source="internos",
        )
        if not r.get("ok"):
            return self._ok(f"Error al limpiar: {r.get('error')}", state)
        d     = r.get("data") or {}
        total = sum((d.get("borrados") or {}).values())
        return self._ok(
            f"✓ Seed <code>{label}</code> eliminado — {total} registros borrados.",
            state,
            reply_markup={"inline_keyboard": [[{"text": "Ver seeds", "callback_data": "/seeds"}]]}
        )

    # -------------------------------------------------------------------------
    # Candidate pipeline (normal text)
    # -------------------------------------------------------------------------

    def _candidato_pipeline(self, update: dict, state: dict) -> dict:
        message       = update.get("message", {})
        text          = (message.get("text") or "").strip()
        user_id       = str((message.get("from") or {}).get("id", ""))

        # Need a vacante to capture candidates — ask user to pick one
        vacante_id = state.get("pipeline_vacante_id", "")
        if not vacante_id:
            return self._pedir_vacante_pipeline(state)

        route_r = self._get_runner().run("bot_inbox_router", {
            "canal":      "telegram",
            "user_id":    user_id,
            "empresa_id": _EMPRESA_ID,
            "vacante_id": vacante_id,
        }, source="internos")
        if not route_r.get("ok"):
            return self._ok(f"Error de enrutamiento: {route_r.get('error')}", state)

        route           = route_r.get("data") or {}
        candidate_id    = route.get("candidate_id")
        conversation_id = route.get("conversation_id")

        if not candidate_id or not conversation_id:
            return self._ok("No se pudo identificar al candidato.", state)
        if route.get("requiere_humano"):
            return self._ok("Tu perfil ya fue registrado. El equipo de RH te contactará pronto.", state)

        preguntas = self._get_preguntas(vacante_id)
        if not preguntas:
            return self._ok("Esta vacante no tiene cuestionario. Genera un seed con /seed 1 primero.", state)

        form_r = self._get_runner().run("bot_form_capture", {
            "conversation_id": conversation_id,
            "candidato_id":    candidate_id,
            "vacante_id":      vacante_id,
            "preguntas":       preguntas,
            "message_text":    text,
        }, source="internos")
        if not form_r.get("ok"):
            return self._ok(f"Error en formulario: {form_r.get('error')}", state)

        form = form_r.get("data") or {}
        if form.get("completado"):
            # Auto-score in background would be ideal; for now send thank you
            return self._ok(
                "¡Gracias por completar el formulario!\n"
                "Tu perfil será evaluado por el equipo de RH.",
                state,
            )
        pregunta = form.get("pregunta_siguiente")
        if pregunta:
            paso  = form.get("paso_actual", 1)
            total = form.get("total_pasos", len(preguntas))
            return self._ok(f"[{paso}/{total}] {pregunta}", state)

        return self._ok("Procesando...", state)

    def _pedir_vacante_pipeline(self, state: dict) -> dict:
        db   = SupabaseClient({})
        rows = self._get_vacantes(db)
        if not rows:
            return self._ok("No hay vacantes. Usa /seed 1 para generar datos.", state)
        lines   = ["Selecciona una vacante para capturar candidatos:"]
        buttons = []
        for v in rows[:8]:
            folio  = v.get("folio", "?")
            titulo = v.get("titulo", "?")
            lines.append(f"{folio} — {titulo}")
            buttons.append([{"text": f"{folio} — {titulo[:30]}", "callback_data": f"/pipeline {folio}"}])
        return self._ok("\n".join(lines), state, reply_markup={"inline_keyboard": buttons})

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _get_vacantes(self, db: SupabaseClient) -> list:
        r = db.rest_select("vacantes", select="id,folio,titulo,tipo,estado")
        return (r.get("data") or []) if r.get("ok") else []

    def _resolver_vacante(self, arg: str) -> dict | None:
        db  = SupabaseClient({})
        arg = arg.upper()
        # By folio (VAC-001)
        if arg.startswith("VAC-"):
            r = db.rest_select("vacantes", filters={"folio": arg}, select="id,folio,titulo,tipo", limit=1)
        else:
            # By number (1, 2, 3)
            try:
                n = int(arg)
                folio = f"VAC-{n:03d}"
                r = db.rest_select("vacantes", filters={"folio": folio}, select="id,folio,titulo,tipo", limit=1)
            except ValueError:
                return None
        rows = (r.get("data") or []) if r.get("ok") else []
        return rows[0] if rows else None

    def _get_preguntas(self, vacante_id: str) -> list:
        db = SupabaseClient({})
        r  = db.rest_select("cuestionarios", filters={"vacante_id": vacante_id}, select="preguntas", limit=1)
        rows = (r.get("data") or []) if r.get("ok") else []
        if not rows:
            return []
        p = rows[0].get("preguntas")
        return p if isinstance(p, list) else []

    def _pedir_vacante(self, comando: str, state: dict) -> dict:
        db   = SupabaseClient({})
        rows = self._get_vacantes(db)
        if not rows:
            return self._ok("No hay vacantes. Usa /seed 1 primero.", state)
        lines   = [f"Elige una vacante para /{comando}:"]
        buttons = []
        for v in rows[:8]:
            folio  = v.get("folio", "?")
            titulo = v.get("titulo", "?")
            lines.append(f"{folio} — {titulo}")
            buttons.append([{"text": f"{folio}", "callback_data": f"/{comando} {folio}"}])
        return self._ok("\n".join(lines), state, reply_markup={"inline_keyboard": buttons})

    def _ayuda_buttons(self) -> dict:
        return {"inline_keyboard": [
            [{"text": "Vacantes", "callback_data": "/vacantes"},
             {"text": "Status", "callback_data": "/status"}],
            [{"text": "Seed", "callback_data": "/seed 1"},
             {"text": "Seeds", "callback_data": "/seeds"}],
            [{"text": "Dashboard", "url": _DASHBOARD}],
        ]}

    def _ok(self, response: str, state: dict, reply_markup: dict | None = None) -> dict:
        data: dict = {"response": response, "state": state}
        if reply_markup:
            data["reply_markup"] = reply_markup
        return {"ok": True, "data": data}
