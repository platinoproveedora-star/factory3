from __future__ import annotations
import os
import base64
import json
import importlib.util as _ilu
import urllib.request
import urllib.parse
from datetime import datetime, timezone, date
from pathlib import Path

# ── ai_interpreter (Haiku Vision) ──────────────────────────────────────────
_AI_PATH = Path(__file__).parent.parent.parent / "vertical_factory_utils" / "ai_interpreter" / "service.py"
_ai_spec = _ilu.spec_from_file_location("ai_interpreter_svc", _AI_PATH)
_ai      = _ilu.module_from_spec(_ai_spec)
_ai_spec.loader.exec_module(_ai)


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
    empresa_id   = ctx.get("empresa_id") or ctx.get("company_id") or "EMP_DURALON"
    project_code = ctx.get("project_code", "PROY-001")
    module_code  = ctx.get("module_code", "gastos")
    try:
        # Buscar si existe usuario con mismo nombre y sin chat_id (pre-registrado)
        rows_preexist = _rest_get(
            schema, "usuarios",
            f"nombre=ilike.{urllib.parse.quote(nombre)}&telegram_chat_id=is.null&activo=eq.true"
        )
        if rows_preexist:
            updated = _rest_patch(
                schema, "usuarios",
                {"telegram_chat_id": chat_id},
                f"id=eq.{rows_preexist[0]['id']}"
            )
            user = updated[0] if updated else rows_preexist[0]
            return {"ok": True, "data": {"user": user, "folio": user.get("folio"), "linked": True}}
        folio = _next_folio(schema, "usuarios", "USR")
        row   = _rest_post(schema, "usuarios", {
            "folio":            folio,
            "nombre":           nombre,
            "telegram_chat_id": chat_id,
            "rol":              ctx.get("rol", "capturista"),
            "empresa_id":       empresa_id,
            "project_code":     project_code,
            "module_code":      module_code,
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

        empresa_id   = ctx.get("empresa_id") or ctx.get("company_id") or "EMP_DURALON"
        project_code = ctx.get("project_code", "PROY-001")
        module_code  = ctx.get("module_code", "gastos")

        folio = _next_folio(schema, "gastos", "GAS")
        gasto = _rest_post(schema, "gastos", {
            "folio":            folio,
            "usuario_id":       ctx["usuario_id"],
            "categoria_id":     categoria_id,
            "monto":            monto,
            "descripcion":      ctx.get("descripcion", ""),
            "fecha":            fecha,
            "metodo_captura":   ctx.get("metodo_captura", "manual"),
            "empresa_id":       empresa_id,
            "project_code":     project_code,
            "module_code":      module_code,
            "cost_center_id":   ctx.get("cost_center_id"),
            "customer_id":      ctx.get("customer_id"),
            "supplier_id":      ctx.get("supplier_id"),
            "sales_order_id":   ctx.get("sales_order_id"),
            "purchase_order_id": ctx.get("purchase_order_id"),
            "asset_id":         ctx.get("asset_id"),
            "erp_tags":         ctx.get("erp_tags", {}),
        })

        _rest_post(schema, "gasto_eventos", {
            "gasto_id":    gasto[0]["id"],
            "usuario_id":  ctx["usuario_id"],
            "evento":      "creado",
            "detalle":     {"metodo": ctx.get("metodo_captura", "manual")},
            "empresa_id":  empresa_id,
            "project_code": project_code,
            "module_code": module_code,
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
    """Retorna el SQL DDL para crear todas las tablas del schema (ERP-ready)."""
    sql = f"""-- ============================================================
-- Schema: {schema}
-- Empresa: EMP_DURALON (legacy: UC-101) / PROY-001 / gastos
-- ERP-Ready: empresa_id + project_code + module_code en todas las tablas
-- ============================================================

CREATE SCHEMA IF NOT EXISTS {schema};

-- Usuarios
CREATE TABLE IF NOT EXISTS {schema}.usuarios (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    folio            TEXT UNIQUE NOT NULL,
    nombre           TEXT NOT NULL,
    telegram_chat_id TEXT UNIQUE,
    rol              TEXT NOT NULL DEFAULT 'capturista',
    activo           BOOLEAN NOT NULL DEFAULT true,
    empresa_id       TEXT NOT NULL DEFAULT 'EMP_DURALON',
    project_code     TEXT NOT NULL DEFAULT 'PROY-001',
    module_code      TEXT NOT NULL DEFAULT 'gastos',
    global_user_id   UUID NULL,
    phone            TEXT NULL,
    email            TEXT NULL,
    modules_allowed  TEXT[] NOT NULL DEFAULT ARRAY['gastos'],
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Categorias de gasto
CREATE TABLE IF NOT EXISTS {schema}.categorias_gasto (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre       TEXT UNIQUE NOT NULL,
    activo       BOOLEAN NOT NULL DEFAULT true,
    empresa_id   TEXT NOT NULL DEFAULT 'EMP_DURALON',
    project_code TEXT NOT NULL DEFAULT 'PROY-001',
    module_code  TEXT NOT NULL DEFAULT 'gastos',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Gastos
CREATE TABLE IF NOT EXISTS {schema}.gastos (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    folio             TEXT UNIQUE NOT NULL,
    usuario_id        UUID NOT NULL REFERENCES {schema}.usuarios(id),
    categoria_id      UUID NOT NULL REFERENCES {schema}.categorias_gasto(id),
    monto             NUMERIC(12, 2) NOT NULL,
    descripcion       TEXT,
    fecha             DATE NOT NULL,
    metodo_captura    TEXT NOT NULL DEFAULT 'manual',
    estado            TEXT NOT NULL DEFAULT 'registrado',
    empresa_id        TEXT NOT NULL DEFAULT 'EMP_DURALON',
    project_code      TEXT NOT NULL DEFAULT 'PROY-001',
    module_code       TEXT NOT NULL DEFAULT 'gastos',
    cost_center_id    UUID NULL,
    customer_id       UUID NULL,
    supplier_id       UUID NULL,
    sales_order_id    UUID NULL,
    purchase_order_id UUID NULL,
    asset_id          UUID NULL,
    erp_tags          JSONB NOT NULL DEFAULT '{}',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Documentos (tickets, fotos, comprobantes)
CREATE TABLE IF NOT EXISTS {schema}.gasto_documentos (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    folio        TEXT UNIQUE NOT NULL,
    gasto_id     UUID NOT NULL REFERENCES {schema}.gastos(id),
    url          TEXT NOT NULL,
    tipo         TEXT NOT NULL DEFAULT 'ticket',
    storage_path TEXT,
    empresa_id   TEXT NOT NULL DEFAULT 'EMP_DURALON',
    project_code TEXT NOT NULL DEFAULT 'PROY-001',
    module_code  TEXT NOT NULL DEFAULT 'gastos',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Eventos de auditoria
CREATE TABLE IF NOT EXISTS {schema}.gasto_eventos (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    gasto_id     UUID REFERENCES {schema}.gastos(id),
    usuario_id   UUID REFERENCES {schema}.usuarios(id),
    evento       TEXT NOT NULL,
    detalle      JSONB,
    empresa_id   TEXT NOT NULL DEFAULT 'EMP_DURALON',
    project_code TEXT NOT NULL DEFAULT 'PROY-001',
    module_code  TEXT NOT NULL DEFAULT 'gastos',
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
# OCR — extrae datos de ticket/imagen con Haiku Vision
# ---------------------------------------------------------------------------

def _ocr_ticket(schema: str, ctx: dict) -> dict:
    """Extrae monto/fecha/descripcion/categoria de una imagen de ticket."""
    content_b64 = ctx.get("content_b64", "")
    media_type  = ctx.get("media_type", "image/jpeg")
    categories  = ctx.get("categories", [])

    if not content_b64:
        return {"ok": False, "error": "content_b64 requerido"}

    cat_list = "|".join(categories) if categories else "combustible|gastos varios|taller mecanico|papeleria|gas|internet|nomina|gps|imss|sat"

    schema_ai = {
        "monto":              None,   # número decimal, sin símbolo
        "fecha":              None,   # formato YYYY-MM-DD
        "descripcion":        None,   # concepto corto del gasto
        "categoria_sugerida": None,   # debe ser exactamente una de: cat_list
        "establecimiento":    None,   # nombre del negocio en el ticket
    }

    r = _ai.run({
        "mode":        "extract",
        "schema":      schema_ai,
        "content_b64": content_b64,
        "media_type":  media_type,
        "context":     (
            "Eres un asistente de captura de gastos empresariales. "
            "Analiza el ticket o comprobante y extrae los datos. "
            f"Para categoria_sugerida usa SOLO una de: {cat_list}. "
            "Para fecha usa formato YYYY-MM-DD. "
            "Para monto usa numero decimal sin simbolos ni comas."
        ),
    })

    if not r.get("ok"):
        err = str(r.get("error", ""))
        if "credit" in err.lower() or "billing" in err.lower() or "400" in err:
            return {"ok": False, "error": "Sin creditos de IA — recarga en console.anthropic.com"}
        return r

    extracted = r.get("data", {}).get("extracted", {})

    # Normalizar fecha a YYYY-MM-DD
    fecha = extracted.get("fecha")
    if fecha:
        for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d", "%d-%m-%Y"):
            try:
                fecha = datetime.strptime(str(fecha).strip(), fmt).date().isoformat()
                break
            except (ValueError, AttributeError):
                pass

    # Normalizar monto
    monto = extracted.get("monto")
    if monto is not None:
        try:
            monto = float(str(monto).replace(",", "").replace("$", "").strip())
        except (ValueError, TypeError):
            monto = None

    return {"ok": True, "data": {
        "monto":              monto,
        "fecha":              fecha,
        "descripcion":        extracted.get("descripcion") or extracted.get("establecimiento", ""),
        "categoria_sugerida": extracted.get("categoria_sugerida"),
        "establecimiento":    extracted.get("establecimiento"),
    }}


# ---------------------------------------------------------------------------
# Upload documento — sube imagen a Storage y registra en gasto_documentos
# ---------------------------------------------------------------------------

def _upload_document(schema: str, ctx: dict, dry_run: bool) -> dict:
    """Sube imagen de ticket a Supabase Storage y lo liga al gasto."""
    content_b64 = ctx.get("content_b64", "")
    media_type  = ctx.get("media_type", "image/jpeg")
    gasto_id    = ctx.get("gasto_id", "")
    filename    = ctx.get("filename", "ticket.jpg")
    bucket      = ctx.get("bucket", "")

    if not content_b64:
        return {"ok": False, "error": "content_b64 requerido"}
    if not bucket:
        return {"ok": False, "error": "bucket requerido"}
    if dry_run:
        return {"ok": True, "data": {"dry_run": True}}

    file_bytes = base64.b64decode(content_b64)
    ts   = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    path = f"tickets/{ts}_{filename}"

    req = urllib.request.Request(
        f"{_url()}/storage/v1/object/{bucket}/{path}",
        data=file_bytes, method="POST",
        headers={
            "apikey":        _key(),
            "Authorization": f"Bearer {_key()}",
            "Content-Type":  media_type,
            "x-upsert":      "true",
            "User-Agent":    "FactoryFactory/0.1 (+https://github.com/)",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            r.read()
        doc_url = f"{_url()}/storage/v1/object/public/{bucket}/{path}"
    except Exception as e:
        return {"ok": False, "error": f"Storage upload: {e}"}

    # Registrar en gasto_documentos si tenemos gasto_id
    if gasto_id:
        try:
            folio = _next_folio(schema, "gasto_documentos", "DOC")
            _rest_post(schema, "gasto_documentos", {
                "folio":        folio,
                "gasto_id":     gasto_id,
                "url":          doc_url,
                "tipo":         "ticket",
                "storage_path": path,
            })
        except Exception:
            pass  # No fatal — el archivo ya está subido

    return {"ok": True, "data": {"url": doc_url, "path": path}}


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
            "ocr_ticket":      lambda: _ocr_ticket(schema, context),
            "upload_document": lambda: _upload_document(schema, context, dry_run),
        }

        if action not in actions:
            return {"ok": False, "error": f"action desconocida: {action}. Validas: {list(actions.keys())}"}

        return actions[action]()
