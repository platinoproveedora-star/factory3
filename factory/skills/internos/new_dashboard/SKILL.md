# new_dashboard

Genera un dashboard Streamlit completo para cualquier vertical de Factory3 usando IA. Crea `app.py`, `db.py`, `requirements.txt` y opcionalmente `render.yaml`.

## Input

```json
{
  "titulo": "Factory3 Mass Hiring Dashboard",
  "vertical": "mass_digital_hiring",
  "empresa_env_var": "MDH_EMPRESA_ID",
  "tablas": [
    "candidatos", "vacantes", "pipeline", "scores",
    "entrevistas", "reclutadores", "fb_publicaciones"
  ],
  "output_dir": "dashboard",
  "con_render": true,
  "dry_run": false
}
```

- `titulo` — requerido, título del dashboard
- `tablas` — requerido, lista de tablas Supabase a incluir como secciones
- `empresa_env_var` — nombre de la env var para filtrar por empresa (default: `EMPRESA_ID`)
- `output_dir` — carpeta de salida (default: `dashboard`)
- `con_render` — si genera `render.yaml` (default: `true`)
- `dry_run` — si `true`, no escribe archivos, solo devuelve cuántas líneas generó

## Output

```json
{
  "ok": true,
  "data": {
    "output_dir": "dashboard",
    "archivos_creados": ["app.py", "db.py", "requirements.txt", "render.yaml"],
    "dry_run": false,
    "lineas_app": 280
  }
}
```

## Lo que genera

- **Sidebar** con navegación: Overview + una sección por tabla
- **Overview**: métricas `st.metric()` con conteos de cada tabla
- **Sección por tabla**: filtros + `st.dataframe` con pandas
- **CSS claro profesional**: superficies claras, bordes visibles, texto oscuro y sin reglas globales que rompan inputs/selects
- **Helpers**: `_badge()` con íconos por estado, `_folio()` para folios legibles
- **`@st.cache_data(ttl=30)`** en todas las funciones de datos
- **`db.py`**: conexión Supabase via REST sin dependencias externas

## Modelo usado

`claude-sonnet-4-6` — necesita contexto amplio para generar código coherente

## Dependencias

- `ANTHROPIC_API_KEY`
