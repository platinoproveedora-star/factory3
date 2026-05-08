"""Service for dashboard_updater — actualiza un dashboard Streamlit existente con IA."""

from __future__ import annotations
import json
import os
from pathlib import Path

_BASE = Path(__file__).parent.parent.parent.parent.parent

_PROMPT = """\
Eres un experto en Streamlit y en la plataforma Factory3.

Tu tarea es actualizar el dashboard Streamlit existente aplicando la instrucción del usuario.

## Instrucción del usuario
{instruccion}

## Código actual del dashboard (app.py)
```python
{codigo_actual}
```

{contexto_registry}

{contexto_tablas}

## Reglas de modificación
- Mantén TODO el código existente; solo agrega, modifica o reorganiza lo necesario
- Si hay que agregar una sección nueva: agrégala al sidebar `st.radio` Y crea su bloque `elif page == "..."`
- Si hay que agregar métricas: agrégalas al Overview existente
- Si hay que agregar una tabla nueva: agrega su función `@st.cache_data(ttl=30)` y su sección
- Mantén el mismo estilo visual: CSS oscuro, badges, folios, tabs cuando aplique
- No cambies db.py ni requirements.txt a menos que la instrucción lo pida explícitamente
- Los imports van al inicio del bloque donde se usan (ej. `import pandas as pd` dentro del elif)

## Formato de respuesta
Devuelve un JSON con esta estructura:
{{
  "cambios": ["<descripción cambio 1>", "<descripción cambio 2>"],
  "codigo": "<código Python completo del app.py actualizado>"
}}

El campo "codigo" debe contener el archivo app.py completo y funcional.
Devuelve ÚNICAMENTE el JSON, sin texto adicional.
"""

_REGISTRY_SECTION = """\
## Skills registrados en Factory3
{skills_list}
"""

_TABLAS_SECTION = """\
## Tablas Supabase disponibles
{tablas_list}
"""


class DashboardUpdaterService:

    def ejecutar(self, context: dict) -> dict:
        instruccion      = context.get("instruccion", "")
        app_path         = Path(context.get("app_path", "dashboard/app.py"))
        dry_run          = context.get("dry_run", False)
        incluir_registry = context.get("incluir_registry", True)
        incluir_tablas   = context.get("incluir_tablas", True)

        if not instruccion:
            return {"ok": False, "error": "instruccion es requerida"}
        if not app_path.exists():
            return {"ok": False, "error": f"No se encontró {app_path}"}

        codigo_actual = app_path.read_text(encoding="utf-8")

        contexto_registry = ""
        if incluir_registry:
            contexto_registry = self._cargar_registry()

        contexto_tablas = ""
        if incluir_tablas:
            contexto_tablas = self._cargar_tablas()

        resultado = self._actualizar(instruccion, codigo_actual, contexto_registry, contexto_tablas)
        if not resultado["ok"]:
            return resultado

        if not dry_run:
            app_path.write_text(resultado["codigo"], encoding="utf-8")

        return {
            "ok": True,
            "data": {
                "app_path": str(app_path),
                "cambios":  resultado["cambios"],
                "dry_run":  dry_run,
                "lineas":   len(resultado["codigo"].splitlines()),
                "codigo":   resultado["codigo"] if dry_run else None,
            },
        }

    def _actualizar(self, instruccion: str, codigo_actual: str, ctx_registry: str, ctx_tablas: str) -> dict:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return {"ok": False, "error": "ANTHROPIC_API_KEY no configurada"}

        prompt = _PROMPT.format(
            instruccion=instruccion,
            codigo_actual=codigo_actual,
            contexto_registry=ctx_registry,
            contexto_tablas=ctx_tablas,
        )

        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            msg = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=16000,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = msg.content[0].text.strip()

            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()

            data = json.loads(raw)
            return {
                "ok":     True,
                "cambios": data.get("cambios", []),
                "codigo":  data.get("codigo", ""),
            }
        except json.JSONDecodeError:
            return {"ok": False, "error": f"respuesta IA no es JSON válido: {raw[:300]}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _cargar_registry(self) -> str:
        reg_path = _BASE / "factory" / "skills" / "registry.json"
        if not reg_path.exists():
            return ""
        try:
            reg = json.loads(reg_path.read_text(encoding="utf-8"))
            por_vertical: dict[str, list] = {}
            for nombre, info in reg.items():
                v = info.get("vertical", "sin_vertical")
                por_vertical.setdefault(v, []).append(f"  - {nombre}: {info.get('descripcion','')[:80]}")
            lineas = []
            for v, skills in sorted(por_vertical.items()):
                lineas.append(f"\n**{v}**")
                lineas.extend(skills)
            return _REGISTRY_SECTION.format(skills_list="\n".join(lineas))
        except Exception:
            return ""

    def _cargar_tablas(self) -> str:
        tables_path = _BASE / "docs" / "TABLES.md"
        if not tables_path.exists():
            return ""
        try:
            contenido = tables_path.read_text(encoding="utf-8")
            # Solo el índice (primeras líneas hasta el primer ---)
            lineas = contenido.split("---")[0].strip()
            return _TABLAS_SECTION.format(tablas_list=lineas)
        except Exception:
            return ""
