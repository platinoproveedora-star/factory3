"""Service for new_dashboard — genera un dashboard Streamlit completo con IA."""

from __future__ import annotations
import json
import os
from pathlib import Path

_DB_PY = '''\
"""Supabase connection for dashboard."""
from __future__ import annotations
import json, os, urllib.request


def _key() -> str:
    return (os.environ.get("SUPABASE_KEY")
            or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
            or os.environ.get("SUPABASE_ANON_KEY", ""))


def _headers() -> dict:
    key = _key()
    return {
        "apikey":        key,
        "Authorization": f"Bearer {key}",
        "Content-Type":  "application/json",
    }


def _url(table: str, params: str = "") -> str:
    base = os.environ["SUPABASE_URL"].rstrip("/")
    return f"{base}/rest/v1/{table}?{params}" if params else f"{base}/rest/v1/{table}"


def select(table: str, params: str = "select=*&limit=500") -> list:
    req = urllib.request.Request(_url(table, params), headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())
    except Exception:
        return []


def count(table: str, filters: str = "") -> int:
    headers = {**_headers(), "Prefer": "count=exact", "Range": "0-0"}
    params  = f"select=id&{filters}" if filters else "select=id"
    req = urllib.request.Request(_url(table, params), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            cr = r.headers.get("Content-Range", "0/0")
            return int(cr.split("/")[-1]) if "/" in cr else 0
    except Exception:
        return 0
'''

_REQUIREMENTS = """\
streamlit>=1.35
pandas>=2.0
"""

_RENDER_YAML = """\
services:
  - type: web
    name: {nombre}
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: streamlit run app.py --server.port=$PORT --server.address=0.0.0.0
    envVars:
      - key: SUPABASE_URL
        sync: false
      - key: SUPABASE_KEY
        sync: false
"""

_PROMPT = """\
Genera el código completo de un dashboard Streamlit para Factory3.

## Configuración
Título: {titulo}
Vertical: {vertical}
Empresa env var: {empresa_env_var}
Tablas disponibles: {tablas_str}
Descripción de las tablas:
{tablas_descripcion}

## Requisitos del app.py

1. Importa `streamlit as st` y `from db import select`
2. `st.set_page_config(page_title="{titulo}", page_icon="🏭", layout="wide")`
3. CSS oscuro mínimo igual a este:
```python
st.markdown('<style>[data-testid="metric-container"]{{background:#1e1e2e;border-radius:8px;padding:12px;}}[data-testid="stSidebar"]{{background:#12121c;}}h1,h2,h3{{color:#e0e0ff;}}</style>', unsafe_allow_html=True)
```
4. Variable `_EMPRESA_ID = os.getenv("{empresa_env_var}", "empresa_demo")`
5. Sidebar con `st.radio` para navegar entre: Overview + una sección por tabla
6. Botón "↺ Actualizar" que llama `st.cache_data.clear()` + `st.rerun()`
7. Cada función de datos usa `@st.cache_data(ttl=30)`
8. Overview: métricas con `st.metric()` usando `count()` de `db.py` para cada tabla principal
9. Cada sección de tabla: filtros básicos (texto libre buscar + estado si aplica) + `st.dataframe` con pandas
10. Usar `st.tabs()` cuando una sección tenga sub-vistas lógicas
11. Helper `_badge(estado)` con íconos: activa=🟢 pausada=🟡 cerrada/no_apto/rechazado=🔴 apto=🟢 contratado=🏆
12. Helper `_folio(row, prefix)` que devuelve row["folio"] o prefix+id[:6]+"..."

## Reglas
- Código Python limpio, sin comentarios explicativos excesivos
- `import pandas as pd` dentro de los bloques que lo usen
- Usa `st.expander` para filas con muchos campos
- No inventes columnas que no existen en las tablas descritas
- Devuelve ÚNICAMENTE el código Python, sin markdown, sin bloques de código, sin explicaciones

El código debe empezar directamente con: \\"\\"\\"...dashboard docstring...\\"\\"\\"\\ o con `from __future__ import annotations`
"""


class NewDashboardService:

    def ejecutar(self, context: dict) -> dict:
        valido, error = self._validar(context)
        if not valido:
            return {"ok": False, "error": error}

        titulo         = context["titulo"]
        vertical       = context.get("vertical", "factory")
        tablas         = context.get("tablas", [])
        empresa_env    = context.get("empresa_env_var", "EMPRESA_ID")
        output_dir     = Path(context.get("output_dir", "dashboard"))
        dry_run        = context.get("dry_run", False)
        con_render     = context.get("con_render", True)

        tablas_descripcion = self._describir_tablas(tablas)
        app_code = self._generar_app(titulo, vertical, tablas, empresa_env, tablas_descripcion)
        if not app_code["ok"]:
            return app_code

        archivos = {
            "app.py":          app_code["codigo"],
            "db.py":           _DB_PY,
            "requirements.txt": _REQUIREMENTS,
        }
        if con_render:
            archivos["render.yaml"] = _RENDER_YAML.format(nombre=f"dashboard-{vertical}")

        if not dry_run:
            output_dir.mkdir(parents=True, exist_ok=True)
            for nombre, contenido in archivos.items():
                (output_dir / nombre).write_text(contenido, encoding="utf-8")

        return {
            "ok": True,
            "data": {
                "output_dir":      str(output_dir),
                "archivos_creados": list(archivos.keys()),
                "dry_run":         dry_run,
                "lineas_app":      len(app_code["codigo"].splitlines()),
            },
        }

    def _generar_app(self, titulo, vertical, tablas, empresa_env, tablas_descripcion) -> dict:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return {"ok": False, "error": "ANTHROPIC_API_KEY no configurada"}

        tablas_str = ", ".join(tablas) if tablas else "ninguna especificada"
        prompt = _PROMPT.format(
            titulo=titulo,
            vertical=vertical,
            empresa_env_var=empresa_env,
            tablas_str=tablas_str,
            tablas_descripcion=tablas_descripcion,
        )

        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            msg = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            codigo = msg.content[0].text.strip()
            if codigo.startswith("```"):
                lines = codigo.split("\n")
                codigo = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            return {"ok": True, "codigo": codigo}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _describir_tablas(self, tablas: list) -> str:
        tablas_info = {
            "candidatos":   "id, nombre, telefono, email, canal, canal_user_id, estado, folio, created_at",
            "vacantes":     "id, empresa_id, titulo, descripcion, canal, estado, folio, tipo, created_at",
            "pipeline":     "id, candidato_id, vacante_id, etapa, notas, created_at",
            "scores":       "id, candidato_id, vacante_id, score_total, pasa_knockout, detalle, created_at",
            "respuestas":   "id, candidato_id, vacante_id, pregunta, respuesta, orden, created_at",
            "conversaciones":"id, candidato_id, vacante_id, canal, estado, cuestionario_paso, created_at",
            "cuestionarios":"id, empresa_id, vacante_id, puesto, profundidad, canal, preguntas, created_at",
            "entrevistas":  "id, candidato_id, reclutador_id, vacante_id, fecha_hora, duracion_min, tipo, estado, notas, created_at",
            "reclutadores": "id, nombre, telegram_chat_id, empresa_id, zona, activo, created_at",
            "alertas":      "id, candidato_id, tipo, canal, mensaje, enviado, created_at",
            "bot_states":   "id, chat_id, state, updated_at",
            "test_seeds":   "id, seed_label, empresa_id, tabla, registro_id, created_at",
            "fb_grupos":    "id, url, slug, nombre, region, vertical, activo, created_at",
            "fb_publicaciones": "id, vacante_id, empresa_id, grupo_url, grupo_nombre, publicado, dry_run, fecha, created_at",
            "whatsapp_broadcasts": "id, destino, texto, enviado, backend, vacante_id, empresa_id, fecha, created_at",
            "onboarding_docs": "id, candidato_id, empresa_id, doc_clave, doc_nombre, estado, created_at",
        }
        lineas = []
        for t in tablas:
            campos = tablas_info.get(t, "id, created_at")
            lineas.append(f"- {t}: {campos}")
        return "\n".join(lineas) if lineas else "No se especificaron tablas"

    def _validar(self, context: dict) -> tuple[bool, str | None]:
        if not context.get("titulo"):
            return False, "titulo es requerido"
        if not context.get("tablas"):
            return False, "tablas es requerido (lista de nombres de tablas Supabase)"
        return True, None
