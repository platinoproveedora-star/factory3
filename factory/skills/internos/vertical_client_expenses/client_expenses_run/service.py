from __future__ import annotations
import os
import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone, date


# ---------------------------------------------------------------------------
# HTTP helpers — Supabase REST con schema header
# ---------------------------------------------------------------------------

def _url() -> str:
    return os.getenv("SUPABASE_URL", "").rstrip("/")


def _key() -> str:
    return os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")


def _headers_get(schema: str) -> dict:
    return {
        "apikey": _key(),
        "Authorization": f"Bearer {_key()}",
        "Accept-Profile": schema,
        "Content-Type": "application/json",
    }


def _headers_write(schema: str) -> dict:
    return {
        "apikey": _key(),
        "Authorization": f"Bearer {_key()}",
        "Content-Profile": schema,
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def _rest_get(schema: str, table: str, params: str = "") -> list:
    url = f"{_url()}/rest/v1/{table}"
    if params:
        url += f"?{params}"
    req = urllib.request.Request(url, headers=_headers_get(schema))
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def _rest_post(schema: str, table: str, data: dict) -> list:
    url = f"{_url()}/rest/v1/{table}"
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode(),
        headers=_headers_write(schema),
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def _rest_patch(schema: str, table: str, data: dict, filter_param: str) -> list:
    url = f"{_url()}/rest/v1/{table}?{filter_param}"
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode(),
        headers=_headers_write(schema),
        method="PATCH",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


# ---------------------------------------------------------------------------
# Folio generator
# ---------------------------------------------------------------------------

def _next_folio(schema: str, table: str, prefix: str) -> str:
    """Genera siguiente folio: GAS-001, USR-001, DOC-001, etc."""
    try:
        rows = _rest_get(schema, table, "select=folio&order=folio.desc&limit=1")
        if rows and rows[0].get("folio"):
            num = int(rows[0]["folio"].split("-")[1]) + 1
        else:
            num = 1
        return f"{prefix}-{num:03d}"
    except Exception:
        return f"{prefix}-001"


# ---------------------------------------------------------------------------
# Acciones
# ---------------------------------------------------------------------------

def _get_categories(schema: str, ctx: dict) -> dict:
    """Lista categorias activas del schema."""
    try:
        rows = _rest_get(schema, "categorias_gasto", "activo=eq.true&order=nombre.asc")
        return {"ok": True, "data": {"categorias": [r["nombre"] for r in rows]}}
    except Exception as e:
        return {"ok": False, "error": f"get_categories: {e}"}


def _get_user(schema: str, ctx: dict) -> dict:
    """Busca usuario por telegram_chat_id."""
    chat_id = str(ctx.get("telegram_chat_id", ""))
    if not chat_id:
        return {"ok": False, "error": "telegram_chat_id requerido"}
    try:
        rows = _rest_get(
            schema, "usuarios",
            f"telegram_chat_id=eq.{urllib.parse.quote(chat_id)}&activo=eq.true"
        )
        if rows:
            return {"ok": True, "data": {"user": rows[0], "found": True}}
        return {"ok": True, "data": {"user": None, "found": False}}
    except Exception as e:
        return {"ok": False, "error": f"get_user: {e}"}


def _register_user(schema: str, ctx: dict, dry_run: bool) -> dict:
    """
    Registra usuario nuevo por nombre y telegram_chat_id.
    Si ya existe un registro con ese nombre pero sin chat_id, vincula el chat_id.
    """
    nombre  = ctx.get("nombre", "").strip()
    chat_id = str(ctx.get("telegram_chat_id", "")).strip()
    if not nombre or not chat_id:
        return {"ok": False, "error": "nombre y telegram_chat_id requeridos"}
    if dry_run:
        return {"ok": True, "data": {"dry_run": True, "nombre": nombre, "chat_id": chat_id}}
    try:
        # Buscar si existe usuario con mismo nombre y sin chat_id (pre-registrado)
        rows_preexist = _rest_get(
            schema, "usuarios",
            f"nombre=ilike.{urllib.parse.quote(nombre)}&telegram_chat_id=is.null&activo=eq.true"
        )
        if rows_preexist:
            # Vincular chat_id al registro pre-existente
            updated = _rest_patch(
                schema, "usuarios",
                {"telegram_chat_id": chat_id},
                f"id=eq.{rows_preexist[0]['id']}"
            )
            user = updated[0] if updated else rows_preexist[0]
            return {"ok": True, "data": {"user": user, "folio": user.get("folio"), "linked": True}}
        # Si no existe pre-registro, crear nuevo
        folio = _next_folio(schema, "usuarios", "USR")
        row   = _rest_post(schema, "usuarios", {
            "folio":             folio,
            "nombre":            nombre,
            "telegram_chat_id":  chat_id,
            "rol":               ctx.get("rol", "capturista"),
        })
        return {"ok": True, "data": {"user": row[0] if row else None, "folio": folio}}
    except Exception as e:
        return {"ok": False, "error": f"register_user: {e}"}


def _save_expense(schema: str, ctx: dict, dry_run: bool) -> dict:
    """Guarda un gasto nuevo."""
    required = ["usuario_id", "categoria", "monto"]
    missing = [f for f in required if not ctx.get(f)]
    if missing:
        return {"ok": False, "error": f"Campos requeridos: {missing}"}

    monto = ctx["monto"]
    try:
        monto = float(str(monto).replace(",", "."))
    except ValueError:
        return {"ok": False, "error": f"monto invalido: {monto}"}

    fecha = ctx.get("fecha") or date.today().isoformat()

    if dry_run:
        return {"ok": True, "data": {
            "dry_run": True,
            "preview": {
                "categoria": ctx["categoria"],
                "monto": monto,
                "fecha": fecha,
                "descripcion": ctx.get("descripcion", ""),
            }
        }}

    try:
        # Resolver categoria_id
        rows = _rest_get(
            schema, "categorias_gasto",
            f"nombre=eq.{urllib.parse.quote(ctx['categoria'])}"
        )
        if not rows:
            return {"ok": False, "error": f"Categoria no encontrada: {ctx['categoria']}"}
        categoria_id = rows[0]["id"]

        folio = _next_folio(schema, "gastos", "GAS")
        gasto = _rest_post(schema, "gastos", {
            "folio": folio,
            "usuario_id": ctx["usuario_id"],
            "categoria_id": categoria_id,
            "monto": monto,
            "descripcion": ctx.get("descripcion", ""),
            "fecha": fecha,
            "metodo_captura": ctx.get("metodo_captura", "manual"),
        })

        # Evento de auditoría
        _rest_post(schema, "gasto_eventos", {
            "gasto_id": gasto[0]["id"],
            "usuario_id": ctx["usuario_id"],
            "evento": "creado",
            "detalle": {"metodo": ctx.get("metodo_captura", "manual")},
        })

        return {"ok": True, "data": {"gasto": gasto[0], "folio": folio}}
    except Exception as e:
        return {"ok": False, "error": f"save_expense: {e}"}


def _list_expenses(schema: str, ctx: dict) -> dict:
    """Lista gastos con filtros opcionales."""
    params_parts = ["order=fecha.desc"]

    if ctx.get("usuario_id"):
        params_parts.append(f"usuario_id=eq.{ctx['usuario_id']}")
    if ctx.get("fecha_desde"):
        params_parts.append(f"fecha=gte.{ctx['fecha_desde']}")
    if ctx.get("fecha_hasta"):
        params_parts.append(f"fecha=lte.{ctx['fecha_hasta']}")

    limit = int(ctx.get("limit", 20))
    params_parts.append(f"limit={limit}")

    try:
        rows = _rest_get(schema, "gastos", "&".join(params_parts))
        return {"ok": True, "data": {"gastos": rows, "total": len(rows)}}
    except Exception as e:
        return {"ok": False, "error": f"list_expenses: {e}"}


def _get_stats(schema: str, ctx: dict) -> dict:
    """Estadísticas básicas: total gastado, por categoría, por usuario."""
    try:
        gastos = _rest_get(schema, "gastos", "select=monto,categoria_id,fecha,usuario_id")
        categorias = {r["id"]: r["nombre"] for r in _rest_get(schema, "categorias_gasto", "")}
        usuarios = {r["id"]: r["nombre"] for r in _rest_get(schema, "usuarios", "")}

        total = sum(float(g["monto"]) for g in gastos)

        por_cat: dict = {}
        for g in gastos:
            cat = categorias.get(g["categoria_id"], "desconocida")
            por_cat[cat] = round(por_cat.get(cat, 0.0) + float(g["monto"]), 2)

        por_usr: dict = {}
        for g in gastos:
            usr = usuarios.get(g["usuario_id"], "desconocido")
            por_usr[usr] = round(por_usr.get(usr, 0.0) + float(g["monto"]), 2)

        return {"ok": True, "data": {
            "total": round(total, 2),
            "num_gastos": len(gastos),
            "por_categoria": dict(sorted(por_cat.items(), key=lambda x: -x[1])),
            "por_usuario": dict(sorted(por_usr.items(), key=lambda x: -x[1])),
        }}
    except Exception as e:
        return {"ok": False, "error": f"get_stats: {e}"}


def _get_schema_sql(schema: str, ctx: dict) -> dict:
    """Retorna el SQL DDL para crear todas las tablas del schema."""
    sql = f"""-- ============================================================
-- Schema: {schema}
-- Proyecto: UC-101 / PROY-001
-- Generar en Supabase SQL Editor
-- ============================================================

CREATE SCHEMA IF NOT EXISTS {schema};

-- Usuarios
CREATE TABLE IF NOT EXISTS {schema}.usuarios (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    folio           TEXT UNIQUE NOT NULL,
    nombre          TEXT NOT NULL,
    telegram_chat_id TEXT UNIQUE,
    rol             TEXT NOT NULL DEFAULT 'capturista',
    activo          BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Categorias de gasto
CREATE TABLE IF NOT EXISTS {schema}.categorias_gasto (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre     TEXT UNIQUE NOT NULL,
    activo     BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Gastos
CREATE TABLE IF NOT EXISTS {schema}.gastos (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    folio           TEXT UNIQUE NOT NULL,
    usuario_id      UUID NOT NULL REFERENCES {schema}.usuarios(id),
    categoria_id    UUID NOT NULL REFERENCES {schema}.categorias_gasto(id),
    monto           NUMERIC(12, 2) NOT NULL,
    descripcion     TEXT,
    fecha           DATE NOT NULL,
    metodo_captura  TEXT NOT NULL DEFAULT 'manual',
    estado          TEXT NOT NULL DEFAULT 'registrado',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Documentos (tickets, fotos, comprobantes)
CREATE TABLE IF NOT EXISTS {schema}.gasto_documentos (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    folio        TEXT UNIQUE NOT NULL,
    gasto_id     UUID NOT NULL REFERENCES {schema}.gastos(id),
    url          TEXT NOT NULL,
    tipo         TEXT NOT NULL DEFAULT 'ticket',
    storage_path TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Eventos de auditoria
CREATE TABLE IF NOT EXISTS {schema}.gasto_eventos (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    gasto_id   UUID REFERENCES {schema}.gastos(id),
    usuario_id UUID REFERENCES {schema}.usuarios(id),
    evento     TEXT NOT NULL,
    detalle    JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Seed de categorias iniciales
INSERT INTO {schema}.categorias_gasto (nombre) VALUES
    ('combustible'),
    ('gastos varios'),
    ('taller mecanico'),
    ('papeleria'),
    ('telmex'),
    ('gas'),
    ('internet'),
    ('recargas celulares'),
    ('nomina'),
    ('gps'),
    ('imss'),
    ('sat')
ON CONFLICT (nombre) DO NOTHING;
"""
    return {"ok": True, "data": {"sql": sql, "schema": schema}}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

class ClientExpensesService:
    def ejecutar(self, context: dict) -> dict:
        action = context.get("action", "")
        schema = context.get("schema") or context.get("supabase_schema", "")
        dry_run = context.get("dry_run", True)

        if not action:
            return {"ok": False, "error": "action requerida: get_categories | get_user | register_user | save_expense | list_expenses | get_stats | get_schema_sql"}
        if not schema:
            return {"ok": False, "error": "schema requerido (ej: uc101_proy001)"}

        actions = {
            "get_categories":  lambda: _get_categories(schema, context),
            "get_user":        lambda: _get_user(schema, context),
            "register_user":   lambda: _register_user(schema, context, dry_run),
            "save_expense":    lambda: _save_expense(schema, context, dry_run),
            "list_expenses":   lambda: _list_expenses(schema, context),
            "get_stats":       lambda: _get_stats(schema, context),
            "get_schema_sql":  lambda: _get_schema_sql(schema, context),
        }

        if action not in actions:
            return {"ok": False, "error": f"action desconocida: {action}. Validas: {list(actions.keys())}"}

        return actions[action]()
