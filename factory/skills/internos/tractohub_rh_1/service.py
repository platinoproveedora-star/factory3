"""Orquestador master TractHub RH — Facebook + captura Telegram + evaluacion automatica."""

from __future__ import annotations

import os
from pathlib import Path

from factory.engine import SkillLoader, SkillRunner, SupabaseClient


_BASE = Path(__file__).parent.parent.parent.parent.parent

# ── Config TractHub ────────────────────────────────────────────────────────────
_EMPRESA_ID       = os.getenv("TRACTOHUB_EMPRESA_ID",   "tractohub")
_REGION           = os.getenv("TRACTOHUB_REGION",        "peninsula de yucatan mexico")
_CONTACTO         = os.getenv("TRACTOHUB_CONTACTO",      "")          # link Telegram o telefono
_MANAGER_CHAT_ID  = os.getenv("MANAGER_TELEGRAM_CHAT_ID", "")
_TELEGRAM_TOKEN   = os.getenv("FACTORY3_ADMIN_BOT_TOKEN", "")
_FB_KEYWORDS_BASE = ["choferes", "operadores", "transportistas", "logistica", "viajes", "camioneros"]
_FB_COOLDOWN_H    = 72   # horas entre publicaciones en el mismo grupo


class TractohubRh1Service:

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
        comando: str = context.get("comando") or ""

        # ── Flujo Facebook ─────────────────────────────────────────────────────
        if comando == "buscar_grupos":
            return self._buscar_grupos(context)

        if comando == "publicar_vacante":
            return self._publicar_vacante(context)

        # ── Flujo candidato (Telegram) ─────────────────────────────────────────
        if comando == "mensaje_entrante":
            return self._mensaje_entrante(context)

        # ── Setup vacante ──────────────────────────────────────────────────────
        if comando == "crear_vacante":
            return self._crear_vacante(context)

        return {"ok": False, "error": f"Comando desconocido: {comando}. Usa: buscar_grupos, publicar_vacante, mensaje_entrante, crear_vacante"}

    # ── Buscar grupos de FB ────────────────────────────────────────────────────

    def _buscar_grupos(self, context: dict) -> dict:
        keywords_extra: list = context.get("keywords_extra") or []
        keywords = _FB_KEYWORDS_BASE + keywords_extra
        return self._get_runner().run("facebook_group_finder", {
            "keywords": keywords,
            "region":   _REGION,
            "limit":    context.get("limit", 20),
            "guardar":  True,
            "vertical": "tractohub",
        }, source="internos")

    # ── Publicar vacante en UN grupo ───────────────────────────────────────────

    def _publicar_vacante(self, context: dict) -> dict:
        vacante_id: str  = context.get("vacante_id") or ""
        grupo_url:  str  = context.get("grupo_url") or ""
        grupo_nombre: str = context.get("grupo_nombre") or ""
        dry_run:    bool = context.get("dry_run", True)
        headless:   bool = context.get("headless", True)

        if not vacante_id or not grupo_url:
            return {"ok": False, "error": "vacante_id y grupo_url son requeridos"}

        runner = self._get_runner()

        # Verificar cooldown
        ck = runner.run("facebook_post_tracker", {
            "accion":        "puede_publicar",
            "grupo_url":     grupo_url,
            "vacante_id":    vacante_id,
            "cooldown_horas": _FB_COOLDOWN_H,
        }, source="internos")
        if ck.get("ok") and not (ck.get("data") or {}).get("puede"):
            return {"ok": False, "error": (ck.get("data") or {}).get("razon", "cooldown activo")}

        # Obtener datos de la vacante
        db  = SupabaseClient({})
        r   = db.rest_select("vacantes", filters={"id": vacante_id}, select="titulo,descripcion,requisitos,salario,ubicacion", limit=1)
        vac = ((r.get("data") or [{}])[0]) if r.get("ok") else {}

        contacto = _CONTACTO or "Escríbenos por este medio"

        # Generar post
        pg = runner.run("facebook_post_generator", {
            "titulo_vacante":      vac.get("titulo", ""),
            "descripcion_vacante": vac.get("descripcion", ""),
            "requisitos":          vac.get("requisitos", ""),
            "salario":             vac.get("salario", ""),
            "ubicacion":           vac.get("ubicacion", _REGION),
            "contacto":            contacto,
            "grupo_nombre":        grupo_nombre,
            "variantes":           1,
        }, source="internos")
        if not pg.get("ok"):
            return {"ok": False, "error": f"Error generando post: {pg.get('error')}"}

        texto = (pg.get("data") or {}).get("recomendada") or ""

        # Publicar
        pub = runner.run("facebook_post_publisher", {
            "grupo_url": grupo_url,
            "texto":     texto,
            "dry_run":   dry_run,
            "headless":  headless,
        }, source="internos")

        publicado = (pub.get("data") or {}).get("publicado", False) or dry_run

        # Registrar
        runner.run("facebook_post_tracker", {
            "accion":       "registrar",
            "vacante_id":   vacante_id,
            "empresa_id":   _EMPRESA_ID,
            "grupo_url":    grupo_url,
            "grupo_nombre": grupo_nombre,
            "texto":        texto,
            "publicado":    publicado and not dry_run,
            "dry_run":      dry_run,
        }, source="internos")

        return {
            "ok":  pub.get("ok", False),
            "data": {
                "grupo_url":  grupo_url,
                "texto":      texto,
                "publicado":  publicado,
                "dry_run":    dry_run,
                "publisher":  pub.get("data"),
            },
        }

    # ── Mensaje entrante de candidato (Telegram) ───────────────────────────────

    def _mensaje_entrante(self, context: dict) -> dict:
        update:     dict = context.get("update") or {}
        state:      dict = context.get("state") or {}
        vacante_id: str  = context.get("vacante_id") or state.get("pipeline_vacante_id") or ""
        message         = update.get("message") or {}
        text:       str  = (message.get("text") or "").strip()
        user_id:    str  = str((message.get("from") or {}).get("id", ""))

        if not vacante_id:
            return {"ok": True, "data": {
                "response": "Indica el ID de la vacante para comenzar.",
                "state": state,
            }}

        runner = self._get_runner()

        # Router
        route_r = runner.run("bot_inbox_router", {
            "canal":      "telegram",
            "user_id":    user_id,
            "empresa_id": _EMPRESA_ID,
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

        # Verificar si el candidato está en modo onboarding (estado = contratado)
        db_check = SupabaseClient({})
        cand_r   = db_check.rest_select("candidatos", filters={"id": candidate_id}, select="estado", limit=1)
        cand_estado = ((cand_r.get("data") or [{}])[0]).get("estado", "")
        if cand_estado == "contratado":
            return self._onboarding_mensaje(candidate_id, update, state)

        # Preguntas del cuestionario
        db        = SupabaseClient({})
        qr        = db.rest_select("cuestionarios", filters={"vacante_id": vacante_id}, select="preguntas", limit=1)
        preguntas = []
        if qr.get("ok") and qr.get("data"):
            p = (qr.get("data") or [{}])[0].get("preguntas")
            preguntas = p if isinstance(p, list) else []

        if not preguntas:
            return {"ok": True, "data": {"response": "Esta vacante aún no tiene cuestionario.", "state": state}}

        # Captura formulario
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

        # Formulario completo → disparar evaluacion automatica
        if form.get("completado"):
            runner.run("rh_post_score_orchestrator", {
                "candidato_id":       candidate_id,
                "vacante_id":         vacante_id,
                "empresa_id":         _EMPRESA_ID,
                "manager_chat_id":    _MANAGER_CHAT_ID,
                "telegram_token":     _TELEGRAM_TOKEN,
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

    # ── Onboarding de documentos (candidato contratado) ───────────────────────

    def _onboarding_mensaje(self, candidate_id: str, update: dict, state: dict) -> dict:
        db = SupabaseClient({})

        # Ver si ya tiene docs pendientes (onboarding iniciado)
        r         = db.rest_select("onboarding_docs", filters={"candidato_id": candidate_id, "estado": "pendiente"}, select="id", limit=1)
        pendientes = (r.get("data") or []) if r.get("ok") else []

        accion = "procesar_mensaje" if pendientes else "iniciar"

        result = self._get_runner().run("tractohub_driver_onboarding", {
            "accion":       accion,
            "candidato_id": candidate_id,
            "empresa_id":   _EMPRESA_ID,
            "update":       update,
        }, source="internos")

        if not result.get("ok"):
            return {"ok": True, "data": {"response": "Error en onboarding.", "state": state}}

        data = result.get("data") or {}
        return {"ok": True, "data": {"response": data.get("response", ""), "state": state}}

    # ── Crear vacante completa ─────────────────────────────────────────────────

    def _crear_vacante(self, context: dict) -> dict:
        runner = self._get_runner()

        # Guardar vacante
        vac_r = runner.run("rh_vacante_store", {
            "accion":      "crear",
            "empresa_id":  _EMPRESA_ID,
            "titulo":      context.get("titulo") or "",
            "descripcion": context.get("descripcion") or "",
            "requisitos":  context.get("requisitos") or "",
            "salario":     context.get("salario") or "",
            "ubicacion":   context.get("ubicacion") or _REGION,
        }, source="internos")
        if not vac_r.get("ok"):
            return {"ok": False, "error": f"Error creando vacante: {vac_r.get('error')}"}

        vacante_id = (vac_r.get("data") or {}).get("id") or (vac_r.get("data") or {}).get("vacante_id")

        # Generar cuestionario
        qr = runner.run("rh_questionnaire_generator", {
            "vacante_id":  vacante_id,
            "empresa_id":  _EMPRESA_ID,
            "titulo":      context.get("titulo") or "",
            "descripcion": context.get("descripcion") or "",
            "profundidad": context.get("profundidad", "simple"),
            "canal":       "telegram",
            "guardar":     True,
        }, source="internos")

        return {
            "ok": True,
            "data": {
                "vacante_id":  vacante_id,
                "cuestionario": (qr.get("data") or {}).get("preguntas"),
                "vacante":     vac_r.get("data"),
            },
        }
