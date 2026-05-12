"""Bot mode fbgroups — FB Groups Discovery en Telegram."""
from __future__ import annotations

import os
from pathlib import Path

from factory.engine import SkillLoader, SkillRunner, SupabaseClient

_BASE       = Path(__file__).parent.parent.parent.parent.parent  # factory3 root
_EMPRESA_ID = os.getenv("FB_EMPRESA_ID", os.getenv("RH_EMPRESA_ID", "empresa_1"))

_AYUDA = (
    "<b>FB Groups Discovery</b>\n\n"
    "<b>Búsquedas</b>\n"
    "/buscar — Nueva búsqueda de grupos\n"
    "/misbusquedas — Ver historial de búsquedas\n"
    "/ver SRCH-0001 — Ver grupos de una búsqueda\n"
    "/borrar SRCH-0001 — Eliminar búsqueda y sus grupos\n\n"
    "<b>General</b>\n"
    "/estado — Estado del módulo\n"
    "/ayuda — Esta ayuda\n"
    "/salir — Salir del modo"
)


class FbgroupsRunService:

    def ejecutar(self, context: dict) -> dict:
        update  = context.get("update", {})
        state   = context.get("state", {})
        message = update.get("message", {})
        text    = (message.get("text") or "").strip()

        # Normaliza "/fbgroups buscar" → "/buscar"
        if text.lower().startswith("/fbgroups "):
            text = "/" + text[len("/fbgroups "):].strip()

        parts = text.split(None, 1)
        cmd   = parts[0].lower() if parts else ""
        arg   = parts[1].strip() if len(parts) > 1 else ""
        step  = state.get("fbgroups_step", "")

        # Texto libre cuando se espera el tema de búsqueda
        if step == "awaiting_topic" and not cmd.startswith("/"):
            return self._ejecutar_busqueda(text, state, message)

        if cmd in ("/ayuda", "/help"):
            return self._ok(_AYUDA, state, reply_markup=self._menu_buttons())

        if cmd == "/buscar":
            if arg:
                return self._ejecutar_busqueda(arg, state, message)
            return self._ok(
                "¿Qué tema deseas buscar?\n\nEjemplos:\n"
                "• operadores de tráiler Mérida\n"
                "• cemento México\n"
                "• maquinaria pesada Chiapas",
                {**state, "fbgroups_step": "awaiting_topic"},
            )

        if cmd == "/misbusquedas":
            return self._cmd_misbusquedas(state)

        if cmd == "/ver":
            return self._cmd_ver(arg, state)

        if cmd == "/borrar":
            return self._cmd_borrar(arg, state)

        if cmd == "/estado":
            return self._cmd_estado(state)

        return self._ok(
            "Comando no reconocido. Escribe /ayuda para ver los disponibles.",
            state,
            reply_markup=self._menu_buttons(),
        )

    # ── Comandos ──────────────────────────────────────────────────────────────

    def _ejecutar_busqueda(self, tema: str, state: dict, message: dict) -> dict:
        user_id  = str((message.get("from") or {}).get("id", ""))
        runner   = self._get_runner()
        new_state = {k: v for k, v in state.items() if k != "fbgroups_step"}

        # Paso 1: buscar
        engine_r = runner.run(
            "vertical_fb/fb_groupsearch_engine",
            {"tema_busqueda": tema, "dry_run": False},
            source="internos",
        )
        if not engine_r.get("ok"):
            return self._ok(f"Error en búsqueda: {engine_r.get('error', 'desconocido')}", new_state)

        engine_data = engine_r.get("data") or {}
        grupos      = engine_data.get("grupos", [])
        fuente      = engine_data.get("fuente", "ia_sugerido")

        # Paso 2: guardar
        saver_r = runner.run(
            "vertical_fb/fb_groupsearch_saver",
            {
                "grupos":          grupos,
                "fuente":          fuente,
                "tema_busqueda":   tema,
                "empresa_id":      _EMPRESA_ID,
                "usuario_id":      user_id,
                "dry_run":         False,
            },
            source="internos",
        )
        if not saver_r.get("ok"):
            return self._ok(f"Error al guardar: {saver_r.get('error', 'desconocido')}", new_state)

        d         = saver_r.get("data") or {}
        search_id = d.get("search_id", "")
        total     = d.get("total_grupos", 0)
        estado    = d.get("estado", "completada")
        fuente_lbl = "Meta API" if fuente == "meta_api" else "IA sugerido"

        msg = (
            f"Búsqueda completada.\n\n"
            f"<b>Tema:</b> {tema}\n"
            f"<b>ID:</b> <code>{search_id}</code>\n"
            f"<b>Grupos guardados:</b> {total}\n"
            f"<b>Fuente:</b> {fuente_lbl}"
        )
        if fuente == "ia_sugerido":
            msg += "\n\n<i>⚠️ Grupos generados por IA — no verificados en Facebook</i>"

        buttons = []
        if total > 0:
            buttons.append([{"text": f"Ver grupos ({total})", "callback_data": f"/ver {search_id}"}])
        buttons.append([
            {"text": "Nueva búsqueda", "callback_data": "/buscar"},
            {"text": "Mis búsquedas",  "callback_data": "/misbusquedas"},
        ])

        return self._ok(msg, new_state, reply_markup={"inline_keyboard": buttons})

    def _cmd_misbusquedas(self, state: dict) -> dict:
        db   = SupabaseClient({})
        r    = db.rest_select(
            "fb_gs_searches",
            select="search_id,tema_busqueda,total_grupos,estado,fuente,created_at",
            limit=15,
            order="created_at.desc",
        )
        rows = (r.get("data") or []) if r.get("ok") else []

        if not rows:
            return self._ok(
                "No hay búsquedas guardadas.\nUsa /buscar para iniciar una.",
                state,
                reply_markup={"inline_keyboard": [[{"text": "Nueva búsqueda", "callback_data": "/buscar"}]]},
            )

        lines   = ["<b>Mis búsquedas:</b>\n"]
        buttons = []
        for row in rows:
            sid    = row.get("search_id", "?")
            tema   = (row.get("tema_busqueda") or "")[:30]
            total  = row.get("total_grupos", 0)
            fuente = "🤖" if row.get("fuente") == "ia_sugerido" else "📡"
            lines.append(f"{fuente} <code>{sid}</code> — {tema} [{total} grupos]")
            buttons.append([{"text": f"{sid} — {tema[:22]}", "callback_data": f"/ver {sid}"}])

        buttons.append([{"text": "Nueva búsqueda", "callback_data": "/buscar"}])
        return self._ok("\n".join(lines), state, reply_markup={"inline_keyboard": buttons})

    def _cmd_ver(self, search_id: str, state: dict) -> dict:
        if not search_id:
            return self._ok("Uso: /ver SRCH-0001", state)

        db   = SupabaseClient({})
        r    = db.rest_select(
            "fb_gs_groups",
            filters={"search_id": search_id},
            select="grupo_nombre,grupo_url,descripcion,miembros_estimados,ubicacion_detectada,fuente",
            limit=25,
        )
        rows = (r.get("data") or []) if r.get("ok") else []

        if not rows:
            return self._ok(f"No hay grupos para {search_id}.", state)

        lines = [f"<b>Grupos — {search_id}</b> ({len(rows)} resultados)\n"]
        for g in rows:
            nombre    = g.get("grupo_nombre") or "Sin nombre"
            url       = g.get("grupo_url") or ""
            miembros  = g.get("miembros_estimados")
            ubicacion = g.get("ubicacion_detectada") or ""
            fuente    = g.get("fuente") or ""

            m_txt  = f" | {miembros:,} miembros" if miembros else ""
            loc    = f" | {ubicacion}" if ubicacion else ""
            ia_tag = " ⚠️" if fuente == "ia_sugerido" else ""

            if url:
                lines.append(f"• <a href='{url}'>{nombre}</a>{m_txt}{loc}{ia_tag}")
            else:
                lines.append(f"• <b>{nombre}</b>{m_txt}{loc}{ia_tag}")

        buttons = [[
            {"text": "Borrar búsqueda", "callback_data": f"/borrar {search_id}"},
            {"text": "Mis búsquedas",   "callback_data": "/misbusquedas"},
        ]]
        return self._ok("\n".join(lines), state, reply_markup={"inline_keyboard": buttons})

    def _cmd_borrar(self, search_id: str, state: dict) -> dict:
        if not search_id:
            return self._ok("Uso: /borrar SRCH-0001", state)

        runner = self._get_runner()
        r = runner.run(
            "vertical_fb/fb_groupsearch_delete",
            {"search_id": search_id, "dry_run": False},
            source="internos",
        )
        if not r.get("ok"):
            return self._ok(f"Error al borrar: {r.get('error', 'desconocido')}", state)

        return self._ok(
            f"Búsqueda <code>{search_id}</code> y sus grupos eliminados.",
            state,
            reply_markup={"inline_keyboard": [[{"text": "Mis búsquedas", "callback_data": "/misbusquedas"}]]},
        )

    def _cmd_estado(self, state: dict) -> dict:
        db   = SupabaseClient({})
        r    = db.rest_select("fb_gs_searches", select="total_grupos,estado,fuente", limit=9999)
        rows = (r.get("data") or []) if r.get("ok") else []

        total_busq   = len(rows)
        total_grupos = sum(row.get("total_grupos", 0) for row in rows)
        completadas  = sum(1 for row in rows if row.get("estado") == "completada")
        via_api      = sum(1 for row in rows if row.get("fuente") == "meta_api")
        via_ia       = sum(1 for row in rows if row.get("fuente") == "ia_sugerido")

        msg = (
            f"<b>Estado FB Groups</b>\n\n"
            f"Búsquedas totales:  <b>{total_busq}</b>\n"
            f"Completadas:        <b>{completadas}</b>\n"
            f"Grupos en BD:       <b>{total_grupos}</b>\n"
            f"Via Meta API:       <b>{via_api}</b>\n"
            f"Via IA sugerido:    <b>{via_ia}</b>"
        )
        return self._ok(msg, state, reply_markup={"inline_keyboard": [
            [{"text": "Mis búsquedas", "callback_data": "/misbusquedas"},
             {"text": "Nueva búsqueda", "callback_data": "/buscar"}],
        ]})

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _get_runner(self) -> SkillRunner:
        ext = _BASE / "factory" / "skills" / "externos"
        ext.mkdir(parents=True, exist_ok=True)
        loader = SkillLoader(
            internal_root=_BASE / "factory" / "skills" / "internos",
            external_root=ext,
        )
        return SkillRunner(loader)

    def _menu_buttons(self) -> dict:
        return {"inline_keyboard": [
            [{"text": "Buscar grupos",  "callback_data": "/buscar"},
             {"text": "Mis búsquedas", "callback_data": "/misbusquedas"}],
            [{"text": "Estado",         "callback_data": "/estado"}],
        ]}

    def _ok(self, response: str, state: dict, reply_markup: dict | None = None) -> dict:
        data: dict = {"response": response, "state": state}
        if reply_markup:
            data["reply_markup"] = reply_markup
        return {"ok": True, "data": data}
