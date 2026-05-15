"""Router WhatsApp: registro por código + modal por usuario + delegación a handler."""
from __future__ import annotations
import importlib.util
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

_UA = "FactoryFactory/0.1 (+https://github.com/)"

_MODO_HANDLERS: dict[str, str] = {
    "logplat": "emp_logplat_message_handler",
}

_MODO_LABELS: dict[str, str] = {
    "logplat": "📦 *logplat* — Platino Logística",
    "rh":      "👥 *rh* — Recursos Humanos",
    "sat":     "🧾 *sat* — SAT / Fiscal",
}

_MSG_NO_ACCESO = (
    "Hola. Para acceder escribe tu *código de acceso*.\n"
    "Si no tienes uno, contacta al administrador."
)


class WabizChannelRouterService:

    def ejecutar(self, context: dict) -> dict:
        empresa_id = context.get("empresa_id", "factory3")
        from_phone = context.get("from_phone")
        msg_type   = context.get("type", "text")
        body       = (context.get("body") or "").strip()
        dry_run    = context.get("dry_run", True)

        if not from_phone:
            return {"ok": False, "error": "from_phone requerido"}

        body_lower = body.lower()
        state      = self._load_state(empresa_id, from_phone)
        user       = self._get_user(from_phone)

        # ── Ayuda ─────────────────────────────────────────────────────────────
        if msg_type == "text" and body_lower in ("ayuda", "/ayuda"):
            active_now = state.get("active_mode", "")
            if not user or not active_now or active_now not in _MODO_HANDLERS:
                return self._reply(self._txt_ayuda(user), empresa_id, from_phone, dry_run)
            # con modo activo: delegar al handler para que muestre sus comandos

        # ── No registrado → flujo de registro ─────────────────────────────────
        if not user:
            return self._registro(empresa_id, from_phone, body, msg_type, state, dry_run)

        # ── Salir: limpiar modo activo ─────────────────────────────────────────
        if msg_type == "text" and body_lower in ("salir", "/salir"):
            new_state = {k: v for k, v in state.items() if k != "active_mode"}
            if not dry_run:
                self._save_state(empresa_id, from_phone, new_state)
            return self._reply(self._txt_menu(user), empresa_id, from_phone, dry_run)

        # ── Determinar modo activo ────────────────────────────────────────────
        active_mode = state.get("active_mode", "")
        user_modes  = user.get("user_mode") or []

        if not active_mode:
            if len(user_modes) == 1:
                # Un solo modo: entrar directo sin preguntar
                active_mode = user_modes[0]
                if not dry_run:
                    self._save_state(empresa_id, from_phone, {**state, "active_mode": active_mode})
            elif msg_type == "text" and body_lower in [m.lower() for m in user_modes]:
                # El usuario eligió un modo válido
                active_mode = body_lower
                if not dry_run:
                    self._save_state(empresa_id, from_phone, {**state, "active_mode": active_mode})
                nombre = user.get("nombre", "")
                return self._reply(
                    f"Modo *{active_mode}* activado. Hola {nombre}.\nEscribe *ayuda* para ver los comandos.",
                    empresa_id, from_phone, dry_run,
                )
            else:
                # Varios modos, esperar elección
                return self._reply(self._txt_menu(user), empresa_id, from_phone, dry_run)

        # ── Delegar al handler ────────────────────────────────────────────────
        if active_mode not in _MODO_HANDLERS:
            return self._reply(f"Modo *{active_mode}* no disponible aún.", empresa_id, from_phone, dry_run)

        result = self._run_handler(active_mode, {
            **context,
            "usuario_nombre":     user.get("nombre", ""),
            "usuario_empresa_id": user.get("empresa_id", empresa_id),
            "active_mode":        active_mode,
            "dry_run":            dry_run,
        })

        if not result.get("ok"):
            if not dry_run:
                self._send_text(empresa_id, from_phone, "⚠️ Ocurrió un error. Intenta de nuevo.")
            return result

        reply = result.get("data", {}).get("reply", "")
        if reply and not dry_run:
            self._send_text(empresa_id, from_phone, reply)

        return result

    # ── REGISTRO ──────────────────────────────────────────────────────────────

    def _registro(self, empresa_id, from_phone, body, msg_type, state, dry_run) -> dict:
        reg_step = state.get("reg_step", "")

        if msg_type != "text" or not body:
            if not dry_run:
                self._save_state(empresa_id, from_phone, {**state, "reg_step": "awaiting_code"})
            return self._reply(_MSG_NO_ACCESO, empresa_id, from_phone, dry_run)

        if not reg_step:
            if not dry_run:
                self._save_state(empresa_id, from_phone, {**state, "reg_step": "awaiting_code"})
            return self._reply(_MSG_NO_ACCESO, empresa_id, from_phone, dry_run)

        if reg_step == "awaiting_code":
            code = self._validate_code(body.strip())
            if not code:
                return self._reply("Código incorrecto. Intenta de nuevo.", empresa_id, from_phone, dry_run)
            if not dry_run:
                self._save_state(empresa_id, from_phone, {**state, "reg_step": "awaiting_name", "reg_codigo": body.strip()})
            return self._reply("Código válido ✅\n¿Cuál es tu nombre?", empresa_id, from_phone, dry_run)

        if reg_step == "awaiting_name":
            codigo = state.get("reg_codigo", "")
            code   = self._validate_code(codigo)
            if not code:
                if not dry_run:
                    self._save_state(empresa_id, from_phone, {})
                return self._reply("Sesión expirada. Escribe tu código de nuevo.", empresa_id, from_phone, dry_run)

            nombre    = body.strip()
            user_mode = code.get("user_mode") or []
            role      = code.get("role", "user")
            emp_id    = code.get("empresa_id", empresa_id)

            if not dry_run:
                self._create_user(from_phone, nombre, emp_id, role, user_mode)

            active = user_mode[0] if len(user_mode) == 1 else ""
            if not dry_run:
                self._save_state(empresa_id, from_phone, {"active_mode": active})

            if len(user_mode) == 1:
                reply = f"✅ Bienvenido *{nombre}*.\nModo *{active}* activado. Escribe *ayuda* para ver los comandos."
            else:
                modos_str = "\n".join(_MODO_LABELS.get(m, f"• {m}") for m in user_mode)
                reply = f"✅ Bienvenido *{nombre}*.\n\nElige un módulo:\n{modos_str}"

            return self._reply(reply, empresa_id, from_phone, dry_run)

        # Estado inválido → reiniciar
        if not dry_run:
            self._save_state(empresa_id, from_phone, {})
        return self._reply(_MSG_NO_ACCESO, empresa_id, from_phone, dry_run)

    # ── TEXTOS ────────────────────────────────────────────────────────────────

    def _txt_ayuda(self, user: dict | None) -> str:
        if not user:
            return _MSG_NO_ACCESO
        nombre = user.get("nombre", "")
        modes  = user.get("user_mode") or []
        lines  = [f"Hola *{nombre}*. Tus módulos:\n"]
        for m in modes:
            lines.append(_MODO_LABELS.get(m, f"• {m}"))
        lines.append("\n*Comandos generales:*\n`salir` — cambiar de módulo\n`ayuda` — ver esta ayuda")
        return "\n".join(lines)

    def _txt_menu(self, user: dict) -> str:
        modes  = user.get("user_mode") or []
        nombre = user.get("nombre", "")
        if len(modes) == 1:
            return f"Escribe *{modes[0]}* para continuar."
        lines = [f"Hola *{nombre}*. ¿Qué módulo quieres usar?\n"]
        for m in modes:
            lines.append(_MODO_LABELS.get(m, f"• {m}"))
        return "\n".join(lines)

    # ── SUPABASE ──────────────────────────────────────────────────────────────

    def _get_user(self, phone: str) -> dict | None:
        try:
            qs  = urllib.parse.urlencode({"phone": f"eq.{phone}", "activo": "eq.true", "select": "*", "limit": "1"})
            url = f"{os.getenv('SUPABASE_URL', '').rstrip('/')}/rest/v1/factory_users?{qs}"
            key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
            req = urllib.request.Request(url, headers={
                "apikey": key, "Authorization": f"Bearer {key}",
                "Accept": "application/json", "User-Agent": _UA,
            })
            with urllib.request.urlopen(req, timeout=10) as r:
                rows = json.loads(r.read().decode())
                return rows[0] if rows else None
        except Exception:
            return None

    def _validate_code(self, codigo: str) -> dict | None:
        try:
            qs  = urllib.parse.urlencode({"codigo": f"eq.{codigo}", "activo": "eq.true", "select": "*", "limit": "1"})
            url = f"{os.getenv('SUPABASE_URL', '').rstrip('/')}/rest/v1/wabiz_access_codes?{qs}"
            key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
            req = urllib.request.Request(url, headers={
                "apikey": key, "Authorization": f"Bearer {key}",
                "Accept": "application/json", "User-Agent": _UA,
            })
            with urllib.request.urlopen(req, timeout=10) as r:
                rows = json.loads(r.read().decode())
                return rows[0] if rows else None
        except Exception:
            return None

    def _create_user(self, phone, nombre, empresa_id, role, user_mode) -> None:
        payload = json.dumps({
            "phone": phone, "nombre": nombre, "empresa_id": empresa_id,
            "role": role, "user_mode": user_mode, "activo": True,
        }).encode()
        url = f"{os.getenv('SUPABASE_URL', '').rstrip('/')}/rest/v1/factory_users"
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        try:
            req = urllib.request.Request(url, data=payload, method="POST", headers={
                "apikey": key, "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates,return=minimal",
                "User-Agent": _UA,
            })
            urllib.request.urlopen(req, timeout=10).close()
        except Exception:
            pass

    def _load_state(self, empresa_id: str, from_phone: str) -> dict:
        chat_id = f"wabiz_{empresa_id}_{from_phone}"
        base    = os.getenv("SUPABASE_URL", "").rstrip("/")
        key     = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        try:
            qs  = urllib.parse.urlencode({
                "chat_id": f"eq.{chat_id}",
                "select":  "state",
                "order":   "updated_at.desc",
                "limit":   "1",
            })
            req = urllib.request.Request(f"{base}/rest/v1/bot_states?{qs}", headers={
                "apikey": key, "Authorization": f"Bearer {key}",
                "Accept": "application/json", "User-Agent": _UA,
            })
            with urllib.request.urlopen(req, timeout=10) as r:
                rows = json.loads(r.read().decode())
                return rows[0].get("state") or {} if rows else {}
        except Exception:
            return {}

    def _save_state(self, empresa_id: str, from_phone: str, state: dict) -> None:
        chat_id = f"wabiz_{empresa_id}_{from_phone}"
        base    = os.getenv("SUPABASE_URL", "").rstrip("/")
        key     = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        hdr     = {
            "apikey": key, "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
            "User-Agent": _UA,
        }
        try:
            qs  = urllib.parse.urlencode({"chat_id": f"eq.{chat_id}", "select": "id", "limit": "1"})
            req = urllib.request.Request(f"{base}/rest/v1/bot_states?{qs}",
                                          headers={**hdr, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as r:
                exists = bool(json.loads(r.read().decode()))

            if exists:
                url = f"{base}/rest/v1/bot_states?chat_id=eq.{urllib.parse.quote(chat_id)}"
                req = urllib.request.Request(url,
                                              data=json.dumps({"state": state}).encode(),
                                              method="PATCH", headers=hdr)
            else:
                url = f"{base}/rest/v1/bot_states"
                req = urllib.request.Request(url,
                                              data=json.dumps({"chat_id": chat_id, "state": state}).encode(),
                                              method="POST", headers=hdr)
            urllib.request.urlopen(req, timeout=10).close()
        except Exception:
            pass

    # ── HANDLER + SEND ────────────────────────────────────────────────────────

    def _run_handler(self, mode: str, context: dict) -> dict:
        handler_dir = _MODO_HANDLERS[mode]
        svc_path    = Path(__file__).parent.parent.parent / handler_dir / "service.py"
        try:
            spec = importlib.util.spec_from_file_location(f"{handler_dir}_svc", svc_path)
            mod  = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            cls  = getattr(mod, next(n for n in dir(mod) if n.endswith("Service") and not n.startswith("_")))
            return cls().ejecutar(context)
        except Exception as e:
            return {"ok": False, "error": f"Error en handler {handler_dir}: {e}"}

    def _reply(self, text: str, empresa_id: str, from_phone: str, dry_run: bool) -> dict:
        if not dry_run:
            self._send_text(empresa_id, from_phone, text)
        return {"ok": True, "data": {"reply": text}}

    def _send_text(self, empresa_id: str, to: str, body: str) -> dict:
        try:
            svc_path = Path(__file__).parent.parent / "wabiz_send_text" / "service.py"
            spec     = importlib.util.spec_from_file_location("wabiz_send_text_service", svc_path)
            mod      = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.WabizSendTextService().ejecutar({
                "empresa_id": empresa_id, "to": to, "body": body, "dry_run": False,
            })
        except Exception as e:
            return {"ok": False, "error": str(e)}
