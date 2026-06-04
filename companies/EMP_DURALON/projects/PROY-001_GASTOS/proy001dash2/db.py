"""
Capa de datos — Supabase REST API para schema uc101_proy001.
"""
from __future__ import annotations
import os, json, calendar, urllib.request, urllib.error
from datetime import date, timedelta
import pandas as pd
import streamlit as st

def _get_secret(key: str) -> str:
    val = os.getenv(key, "")
    if not val:
        try:
            import streamlit as _st
            val = _st.secrets.get(key, "")
        except Exception:
            pass
    return val or ""

_SCH = "uc101_proy001"

def _url() -> str:
    return _get_secret("SUPABASE_URL").rstrip("/")

def _key() -> str:
    return _get_secret("SUPABASE_SERVICE_ROLE_KEY")


def _read_headers() -> dict:
    k = _key()
    return {
        "apikey":         k,
        "Authorization":  f"Bearer {k}",
        "Accept-Profile": _SCH,
        "Content-Type":   "application/json",
    }


def _write_headers() -> dict:
    k = _key()
    return {
        "apikey":          k,
        "Authorization":   f"Bearer {k}",
        "Content-Profile": _SCH,
        "Content-Type":    "application/json",
    }


def _get(path: str) -> list:
    req = urllib.request.Request(f"{_url()}/rest/v1/{path}", headers=_read_headers())
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        st.warning(f"GET {path[:60]}: HTTP {e.code}")
        return []
    except Exception as e:
        st.warning(f"GET {path[:60]}: {e}")
        return []


def _post(path: str, body: dict) -> list | dict:
    data = json.dumps(body).encode()
    req  = urllib.request.Request(
        f"{_url()}/rest/v1/{path}",
        data=data,
        headers={**_write_headers(), "Prefer": "return=representation"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.read().decode()[:200]}"}
    except Exception as e:
        return {"error": str(e)}


def _patch(path: str, body: dict) -> bool:
    data = json.dumps(body).encode()
    req  = urllib.request.Request(
        f"{_url()}/rest/v1/{path}",
        data=data,
        headers={**_write_headers(), "Prefer": "return=minimal"},
        method="PATCH",
    )
    try:
        with urllib.request.urlopen(req, timeout=15):
            return True
    except urllib.error.HTTPError as e:
        st.error(f"Error al actualizar: HTTP {e.code} — {e.read().decode()[:200]}")
        return False
    except Exception as e:
        st.error(f"Error al actualizar: {e}")
        return False


def _delete(path: str) -> bool:
    req = urllib.request.Request(
        f"{_url()}/rest/v1/{path}",
        headers=_write_headers(),
        method="DELETE",
    )
    try:
        with urllib.request.urlopen(req, timeout=15):
            return True
    except urllib.error.HTTPError as e:
        st.error(f"Error al eliminar: HTTP {e.code} — {e.read().decode()[:200]}")
        return False
    except Exception as e:
        st.error(f"Error al eliminar: {e}")
        return False


@st.cache_data(ttl=120)
def get_categorias() -> list[str]:
    rows = _get("categorias_gasto?activo=eq.true&order=nombre.asc&select=nombre")
    return [r["nombre"] for r in rows]


@st.cache_data(ttl=120)
def get_usuarios() -> list[dict]:
    return _get("usuarios?activo=eq.true&select=id,nombre,folio")


@st.cache_data(ttl=120)
def get_categoria_id_map() -> dict:
    rows = _get("categorias_gasto?select=id,nombre&activo=eq.true")
    return {r["nombre"]: r["id"] for r in rows}


@st.cache_data(ttl=120)
def get_usuario_id_map() -> dict:
    rows = _get("usuarios?select=id,nombre&activo=eq.true")
    return {r["nombre"]: r["id"] for r in rows}


@st.cache_data(ttl=60)
def get_all_gastos() -> pd.DataFrame:
    rows = _get(
        "gastos"
        "?select=folio,fecha,monto,descripcion,metodo_captura,"
        "categorias_gasto(nombre),usuarios(nombre)"
        "&order=fecha.desc&limit=2000"
    )
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["categoria"]      = df["categorias_gasto"].apply(lambda x: x.get("nombre", "") if isinstance(x, dict) else "")
    df["nombre_usuario"] = df["usuarios"].apply(lambda x: x.get("nombre", "") if isinstance(x, dict) else "")
    df.drop(columns=["categorias_gasto", "usuarios"], inplace=True, errors="ignore")
    df["fecha"]  = pd.to_datetime(df["fecha"])
    df["monto"]  = pd.to_numeric(df["monto"], errors="coerce").fillna(0)
    return df


def get_gastos_mes(year: int, month: int) -> pd.DataFrame:
    first = date(year, month, 1)
    last  = date(year, month, calendar.monthrange(year, month)[1])
    rows  = _get(
        f"gastos?fecha=gte.{first.isoformat()}&fecha=lte.{last.isoformat()}"
        "&select=folio,fecha,monto,descripcion,metodo_captura,"
        "categorias_gasto(nombre),usuarios(nombre)"
        "&order=fecha.asc&limit=500"
    )
    _empty = pd.DataFrame(columns=["folio", "fecha", "categoria", "nombre_usuario",
                                    "monto", "descripcion", "metodo_captura"])
    if not rows:
        return _empty
    df = pd.DataFrame(rows)
    df["categoria"]      = df["categorias_gasto"].apply(lambda x: x.get("nombre", "") if isinstance(x, dict) else "")
    df["nombre_usuario"] = df["usuarios"].apply(lambda x: x.get("nombre", "") if isinstance(x, dict) else "")
    df.drop(columns=["categorias_gasto", "usuarios"], inplace=True, errors="ignore")
    df["fecha"]  = pd.to_datetime(df["fecha"]).dt.date
    df["monto"]  = pd.to_numeric(df["monto"], errors="coerce").fillna(0.0)
    return df[["folio", "fecha", "categoria", "nombre_usuario", "monto", "descripcion", "metodo_captura"]].copy()


def get_meses_disponibles() -> list[tuple[int, int]]:
    rows = _get("gastos?select=fecha&order=fecha.desc&limit=2000")
    meses: set[tuple[int, int]] = set()
    for r in rows:
        try:
            d = date.fromisoformat(r["fecha"][:10])
            meses.add((d.year, d.month))
        except Exception:
            pass
    hoy = date.today()
    meses.add((hoy.year, hoy.month))
    return sorted(meses, reverse=True)


def _next_folio() -> str:
    rows    = _get("gastos?select=folio&order=folio.desc&limit=100")
    max_num = 0
    for r in rows:
        f = r.get("folio", "")
        if f.startswith("GAS-"):
            try:
                max_num = max(max_num, int(f.split("-")[1]))
            except Exception:
                pass
    return f"GAS-{max_num + 1:03d}"


def patch_gasto(folio: str, fields: dict) -> bool:
    return _patch(f"gastos?folio=eq.{folio}", fields)


def delete_gasto(folio: str) -> bool:
    return _delete(f"gastos?folio=eq.{folio}")


def insert_gasto(
    categoria: str,
    usuario: str,
    monto: float,
    fecha: date,
    descripcion: str,
) -> dict:
    cat_map = get_categoria_id_map()
    usr_map = get_usuario_id_map()
    cat_id  = cat_map.get(categoria)
    usr_id  = usr_map.get(usuario)
    if not cat_id:
        return {"error": f"Categoría no encontrada: '{categoria}'"}
    if not usr_id:
        return {"error": f"Usuario no encontrado: '{usuario}'"}
    folio   = _next_folio()
    fecha_s = fecha.isoformat() if hasattr(fecha, "isoformat") else str(fecha)
    body    = {
        "folio":          folio,
        "categoria_id":   cat_id,
        "usuario_id":     usr_id,
        "monto":          float(monto),
        "fecha":          fecha_s,
        "descripcion":    descripcion or "",
        "metodo_captura": "dashboard",
    }
    result = _post("gastos", body)
    if isinstance(result, list) and result:
        return {"ok": True, "folio": folio}
    if isinstance(result, dict) and "error" in result:
        return result
    return {"ok": True, "folio": folio}


def apply_filters(
    df: pd.DataFrame,
    fecha_desde: date | None,
    fecha_hasta: date | None,
    cats: list[str],
    users: list[str],
    monto_min: float,
    monto_max: float,
) -> pd.DataFrame:
    if df.empty:
        return df
    m = pd.Series([True] * len(df), index=df.index)
    if fecha_desde:
        m &= df["fecha"] >= pd.Timestamp(fecha_desde)
    if fecha_hasta:
        m &= df["fecha"] <= pd.Timestamp(fecha_hasta)
    if cats:
        m &= df["categoria"].isin(cats)
    if users:
        m &= df["nombre_usuario"].isin(users)
    m &= df["monto"] >= monto_min
    m &= df["monto"] <= monto_max
    return df[m].copy()


def periodo_dates(
    opcion: str,
    custom_desde: date | None = None,
    custom_hasta: date | None = None,
):
    hoy = date.today()
    if opcion == "Hoy":
        return hoy, hoy
    if opcion == "Esta semana":
        return hoy - timedelta(days=hoy.weekday()), hoy
    if opcion == "Este mes":
        return hoy.replace(day=1), hoy
    if opcion == "Mes anterior":
        primer_actual = hoy.replace(day=1)
        ultimo_ant    = primer_actual - timedelta(days=1)
        return ultimo_ant.replace(day=1), ultimo_ant
    if opcion == "Últimos 3 meses":
        return (hoy.replace(day=1) - timedelta(days=62)).replace(day=1), hoy
    if opcion == "Este año":
        return hoy.replace(month=1, day=1), hoy
    if opcion == "Todo":
        return None, None
    return custom_desde, custom_hasta


def prev_period(fecha_desde: date | None, fecha_hasta: date | None):
    if fecha_desde is None or fecha_hasta is None:
        return None, None
    delta = (fecha_hasta - fecha_desde).days + 1
    return fecha_desde - timedelta(days=delta), fecha_hasta - timedelta(days=delta)
