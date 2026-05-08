"""Orquestador master mass_digital_hiring — genérico, multi-cliente."""

from __future__ import annotations

import os
from pathlib import Path

from factory.engine import SkillLoader, SkillRunner, SupabaseClient

_BASE = Path(__file__).parent.parent.parent.parent.parent


# ── Comandos disponibles ───────────────────────────────────────────────────────
_COMANDOS = (
    "crear_vacante       — crea vacante + cuestionario + QR de entrada\n"
    "planificar_campana  — demand_planner + offer_builder + ad_copy\n"
    "lanzar_campana      — publica en todos los canales configurados\n"
    "buscar_grupos       — busca grupos de Facebook por keywords y región\n"
    "publicar_vacante    — publica en un grupo FB específico\n"
    "mensaje_entrante    — procesa mensaje de candidato (bot)\n"
    "distribuir          — reparte candidatos aptos entre contratistas\n"
    "status              — KPIs del sistema"
)


class MassDigitalHiringRunService:

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

    # ── Config: todo viene del context o cae en env vars ──────────────────────

    def _cfg(self, context: dict, key: str, env_key: str, default: str = "") -> str:
        return context.get(key) or os.getenv(env_key, default)

    def ejecutar(self, context: dict) -> dict:
        comando = (context.get("comando") or "").strip()

        if not comando:
            return {"ok": False, "error": f"comando requerido. Disponibles:\n{_COMANDOS}"}

        if comando == "crear_vacante":
            return self._crear_vacante(context)
        if comando == "planificar_campana":
            return self._planificar_campana(context)
        if comando == "lanzar_campana":
            return self._lanzar_campana(context)
        if comando == "buscar_grupos":
            return self._buscar_grupos(context)
        if comando == "publicar_vacante":
            return self._publicar_vacante(context)
        if comando == "mensaje_entrante":
            return self._mensaje_entrante(context)
        if comando == "distribuir":
            return self._distribuir(context)
        if comando == "status":
            return self._status(context)

        return {"ok": False, "error": f"comando desconocido: '{comando}'. Disponibles:\n{_COMANDOS}"}

    # ── 1. Crear vacante + cuestionario + QR ──────────────────────────────────

    def _crear_vacante(self, context: dict) -> dict:
        empresa_id = self._cfg(context, "empresa_id", "MDH_EMPRESA_ID", "mdh_empresa")
        region     = self._cfg(context, "region", "MDH_REGION", "Mexico")
        bot_url    = self._cfg(context, "bot_url", "MDH_BOT_URL", "")
        runner     = self._get_runner()

        vac_r = runner.run("rh_vacante_store", {
            "accion":      "crear",
            "empresa_id":  empresa_id,
            "titulo":      context.get("titulo") or "",
            "descripcion": context.get("descripcion") or "",
            "requisitos":  context.get("requisitos") or "",
            "salario":     context.get("salario") or "",
            "ubicacion":   context.get("ubicacion") or region,
            "canal":       context.get("canal", "telegram"),
        }, source="internos")
        if not vac_r.get("ok"):
            return {"ok": False, "error": f"Error creando vacante: {vac_r.get('error')}"}

        vacante_id = (vac_r.get("data") or {}).get("id") or (vac_r.get("data") or {}).get("vacante_id")

        qr = runner.run("rh_questionnaire_generator", {
            "vacante_id":  vacante_id,
            "empresa_id":  empresa_id,
            "titulo":      context.get("titulo") or "",
            "descripcion": context.get("descripcion") or "",
            "profundidad": context.get("profundidad", "simple"),
            "canal":       context.get("canal", "telegram"),
            "guardar":     True,
        }, source="internos")

        qr_r = {}
        if bot_url:
            qr_r = runner.run("rh_qr_entry", {
                "bot_url":    bot_url,
                "vacante_id": vacante_id,
                "empresa_id": empresa_id,
            }, source="internos")

        return {
            "ok": True,
            "data": {
                "vacante_id":   vacante_id,
                "vacante":      vac_r.get("data"),
                "cuestionario": (qr.get("data") or {}).get("preguntas"),
                "qr":           qr_r.get("data"),
            },
        }

    # ── 2. Planificar campaña ─────────────────────────────────────────────────

    def _planificar_campana(self, context: dict) -> dict:
        runner     = self._get_runner()
        empresa_id = self._cfg(context, "empresa_id", "MDH_EMPRESA_ID", "mdh_empresa")
        bot_url    = self._cfg(context, "bot_url", "MDH_BOT_URL", "")

        # Demanda
        demanda_r = runner.run("rh_demand_planner", {
            "puesto":           context.get("puesto") or context.get("titulo") or "",
            "demanda_total":    context.get("demanda_total", 10),
            "activos_actuales": context.get("activos_actuales", 0),
            "zona":             context.get("region") or self._cfg(context, "region", "MDH_REGION", ""),
            "tasa_desercion":   context.get("tasa_desercion", 0.20),
        }, source="internos")

        # Oferta
        oferta_r = runner.run("rh_offer_builder", {
            "puesto":       context.get("titulo") or context.get("puesto") or "",
            "empresa":      context.get("empresa") or empresa_id,
            "zona":         context.get("region") or "",
            "salario_min":  context.get("salario_min"),
            "salario_max":  context.get("salario_max"),
            "beneficios":   context.get("beneficios", []),
            "requisitos":   context.get("requisitos_lista", []),
            "notas_extra":  context.get("notas_extra", ""),
        }, source="internos")

        # Copy anuncios
        link_bot = bot_url
        if not link_bot and context.get("vacante_id"):
            qr_r = runner.run("rh_qr_entry", {
                "bot_url":    bot_url or "https://t.me/bot",
                "vacante_id": context.get("vacante_id"),
                "empresa_id": empresa_id,
            }, source="internos")
            link_bot = (qr_r.get("data") or {}).get("link", "")

        copy_r = runner.run("rh_ad_copy_generator", {
            "puesto":     context.get("titulo") or context.get("puesto") or "",
            "empresa":    context.get("empresa") or empresa_id,
            "zona":       context.get("region") or "",
            "salario":    (oferta_r.get("data") or {}).get("salario", ""),
            "requisitos": context.get("requisitos_lista", []),
            "beneficios": context.get("beneficios", []),
            "tono":       context.get("tono", "operativo"),
            "canal":      context.get("canal_principal", "facebook"),
            "variantes":  context.get("variantes_copy", 2),
            "link_bot":   link_bot,
        }, source="internos")

        return {
            "ok": True,
            "data": {
                "demanda":   demanda_r.get("data"),
                "oferta":    oferta_r.get("data"),
                "copies":    (copy_r.get("data") or {}).get("copies", []),
                "link_bot":  link_bot,
            },
        }

    # ── 3. Lanzar campaña (publicar en canales) ───────────────────────────────

    def _lanzar_campana(self, context: dict) -> dict:
        runner  = self._get_runner()
        texto   = context.get("texto") or ""
        canales = context.get("canales", ["facebook"])
        dry_run = context.get("dry_run", True)

        if not texto and context.get("vacante_id"):
            db  = SupabaseClient({})
            r   = db.rest_select("vacantes", filters={"id": context["vacante_id"]}, select="titulo,descripcion", limit=1)
            vac = ((r.get("data") or [{}])[0]) if r.get("ok") else {}
            texto = f"{vac.get('titulo','')} — {vac.get('descripcion','')[:200]}"

        if not texto:
            return {"ok": False, "error": "texto o vacante_id requerido"}

        pub_r = runner.run("rh_channel_publisher", {
            "texto":               texto,
            "canales":             canales,
            "vacante_id":          context.get("vacante_id", ""),
            "empresa_id":          self._cfg(context, "empresa_id", "MDH_EMPRESA_ID", ""),
            "dry_run":             dry_run,
            "whatsapp_destinos":   context.get("whatsapp_destinos", []),
            "telegram_chat_id":    context.get("telegram_chat_id"),
            "base_dir":            "factory",
        }, source="internos")

        return pub_r

    # ── 4. Buscar grupos FB ───────────────────────────────────────────────────

    def _buscar_grupos(self, context: dict) -> dict:
        region   = self._cfg(context, "region", "MDH_REGION", "Mexico")
        keywords = context.get("keywords") or ["trabajo", "empleo", "operadores", "choferes"]
        return self._get_runner().run("facebook_group_finder", {
            "keywords": keywords,
            "region":   region,
            "limit":    context.get("limit", 20),
            "guardar":  True,
            "vertical": context.get("vertical", "mass_digital_hiring"),
        }, source="internos")

    # ── 5. Publicar en un grupo FB ────────────────────────────────────────────

    def _publicar_vacante(self, context: dict) -> dict:
        vacante_id   = context.get("vacante_id") or ""
        grupo_url    = context.get("grupo_url") or ""
        grupo_nombre = context.get("grupo_nombre") or ""
        dry_run      = context.get("dry_run", True)
        empresa_id   = self._cfg(context, "empresa_id", "MDH_EMPRESA_ID", "")
        region       = self._cfg(context, "region", "MDH_REGION", "Mexico")
        cooldown_h   = int(context.get("cooldown_horas", 72))

        if not vacante_id or not grupo_url:
            return {"ok": False, "error": "vacante_id y grupo_url son requeridos"}

        runner = self._get_runner()

        ck = runner.run("facebook_post_tracker", {
            "accion":         "puede_publicar",
            "grupo_url":      grupo_url,
            "vacante_id":     vacante_id,
            "cooldown_horas": cooldown_h,
        }, source="internos")
        if ck.get("ok") and not (ck.get("data") or {}).get("puede"):
            return {"ok": False, "error": (ck.get("data") or {}).get("razon", "cooldown activo")}

        db  = SupabaseClient({})
        r   = db.rest_select("vacantes", filters={"id": vacante_id}, select="titulo,descripcion,requisitos,salario,ubicacion", limit=1)
        vac = ((r.get("data") or [{}])[0]) if r.get("ok") else {}

        pg = runner.run("facebook_post_generator", {
            "titulo_vacante":      vac.get("titulo", ""),
            "descripcion_vacante": vac.get("descripcion", ""),
            "requisitos":          vac.get("requisitos", ""),
            "salario":             vac.get("salario", ""),
            "ubicacion":           vac.get("ubicacion") or region,
            "contacto":            context.get("contacto") or self._cfg(context, "contacto", "MDH_CONTACTO", ""),
            "grupo_nombre":        grupo_nombre,
            "variantes":           1,
        }, source="internos")
        if not pg.get("ok"):
            return {"ok": False, "error": f"Error generando post: {pg.get('error')}"}

        texto = (pg.get("data") or {}).get("recomendada") or ""

        pub = runner.run("facebook_post_publisher", {
            "grupo_url": grupo_url,
            "texto":     texto,
            "dry_run":   dry_run,
            "headless":  context.get("headless", True),
        }, source="internos")

        publicado = (pub.get("data") or {}).get("publicado", False) or dry_run

        runner.run("facebook_post_tracker", {
            "accion":       "registrar",
            "vacante_id":   vacante_id,
            "empresa_id":   empresa_id,
            "grupo_url":    grupo_url,
            "grupo_nombre": grupo_nombre,
            "texto":        texto,
            "publicado":    publicado and not dry_run,
            "dry_run":      dry_run,
        }, source="internos")

        return {
            "ok":  pub.get("ok", False),
            "data": {"grupo_url": grupo_url, "texto": texto, "publicado": publicado, "dry_run": dry_run},
        }

    # ── 6. Mensaje entrante de candidato ──────────────────────────────────────

    def _mensaje_entrante(self, context: dict) -> dict:
        update     = context.get("update") or {}
        state      = context.get("state") or {}
        vacante_id = context.get("vacante_id") or state.get("pipeline_vacante_id") or ""
        empresa_id = self._cfg(context, "empresa_id", "MDH_EMPRESA_ID", "")
        message    = update.get("message") or {}
        text       = (message.get("text") or "").strip()
        user_id    = str((message.get("from") or {}).get("id", ""))

        if not vacante_id:
            return {"ok": True, "data": {"response": "Indica el ID de la vacante para comenzar.", "state": state}}

        runner = self._get_runner()

        route_r = runner.run("bot_inbox_router", {
            "canal":      "telegram",
            "user_id":    user_id,
            "empresa_id": empresa_id,
            "vacante_id": vacante_id,
        }, source="internos")
        if not route_r.get("ok"):
            return {"ok": True, "data": {"response": "Error de enrutamiento.", "state": state}}

        route           = route_r.get("data") or {}
        candidate_id    = route.get("candidate_id")
        conversation_id = route.get("conversation_id")

        if not candidate_id or not conversation_id:
            return {"ok": True, "data": {"response": "No se pudo identificar al candidato.", "state": state}}

        if route.get("requiere_humano"):
            return {"ok": True, "data": {"response": "Tu perfil ya fue registrado. El equipo te contactará pronto.", "state": state}}

        db         = SupabaseClient({})
        cand_r     = db.rest_select("candidatos", filters={"id": candidate_id}, select="estado", limit=1)
        cand_state = ((cand_r.get("data") or [{}])[0]).get("estado", "")

        if cand_state == "contratado" and context.get("onboarding_skill"):
            return self._onboarding_mensaje(candidate_id, empresa_id, update, state, context.get("onboarding_skill"), runner)

        qr        = db.rest_select("cuestionarios", filters={"vacante_id": vacante_id}, select="preguntas", limit=1)
        preguntas = []
        if qr.get("ok") and qr.get("data"):
            p = (qr.get("data") or [{}])[0].get("preguntas")
            preguntas = p if isinstance(p, list) else []

        if not preguntas:
            return {"ok": True, "data": {"response": "Esta vacante aún no tiene cuestionario.", "state": state}}

        form_r = runner.run("bot_form_capture", {
            "conversation_id": conversation_id,
            "candidato_id":    candidate_id,
            "vacante_id":      vacante_id,
            "preguntas":       preguntas,
            "message_text":    text,
        }, source="internos")

        if not form_r.get("ok"):
            return {"ok": True, "data": {"response": "Error en formulario.", "state": state}}

        form = form_r.get("data") or {}

        if form.get("completado"):
            manager_chat_id = self._cfg(context, "manager_chat_id", "MANAGER_TELEGRAM_CHAT_ID", "")
            telegram_token  = self._cfg(context, "telegram_token", "FACTORY3_ADMIN_BOT_TOKEN", "")

            runner.run("rh_post_score_orchestrator", {
                "candidato_id":    candidate_id,
                "vacante_id":      vacante_id,
                "empresa_id":      empresa_id,
                "manager_chat_id": manager_chat_id,
                "telegram_token":  telegram_token,
            }, source="internos")

            if context.get("auto_route_recruiter"):
                runner.run("rh_recruiter_router", {
                    "candidato_id": candidate_id,
                    "empresa_id":   empresa_id,
                    "dry_run":      False,
                    "base_dir":     "factory",
                }, source="internos")

            return {"ok": True, "data": {
                "response": "¡Gracias! Tu perfil fue recibido y está siendo evaluado. Te contactaremos pronto.",
                "state": state,
            }}

        pregunta = form.get("pregunta_siguiente")
        if pregunta:
            paso  = form.get("paso_actual", 1)
            total = form.get("total_pasos", len(preguntas))
            return {"ok": True, "data": {"response": f"[{paso}/{total}] {pregunta}", "state": state}}

        return {"ok": True, "data": {"response": "Procesando...", "state": state}}

    # ── 7. Distribuir candidatos aptos entre contratistas ─────────────────────

    def _distribuir(self, context: dict) -> dict:
        return self._get_runner().run("rh_contractor_splitter", {
            "vacante_id":   context.get("vacante_id"),
            "empresa_ids":  context.get("empresa_ids", []),
            "cupos":        context.get("cupos", {}),
            "score_minimo": context.get("score_minimo", 60.0),
            "estado":       context.get("estado", "apto"),
        }, source="internos")

    # ── 8. Status general ────────────────────────────────────────────────────

    def _status(self, context: dict) -> dict:
        empresa_id = self._cfg(context, "empresa_id", "MDH_EMPRESA_ID", "")
        return self._get_runner().run("rh_stats", {
            "empresa_id": empresa_id,
        }, source="internos")

    # ── Onboarding (opcional, si se configura onboarding_skill) ───────────────

    def _onboarding_mensaje(self, candidate_id, empresa_id, update, state, onboarding_skill, runner) -> dict:
        db        = SupabaseClient({})
        r         = db.rest_select("onboarding_docs", filters={"candidato_id": candidate_id, "estado": "pendiente"}, select="id", limit=1)
        pendientes = (r.get("data") or []) if r.get("ok") else []
        accion    = "procesar_mensaje" if pendientes else "iniciar"

        result = runner.run(onboarding_skill, {
            "accion":       accion,
            "candidato_id": candidate_id,
            "empresa_id":   empresa_id,
            "update":       update,
        }, source="internos")

        if not result.get("ok"):
            return {"ok": True, "data": {"response": "Error en onboarding.", "state": state}}

        return {"ok": True, "data": {"response": (result.get("data") or {}).get("response", ""), "state": state}}
