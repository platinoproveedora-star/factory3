"""Corre dashboard_updater para agregar la sección Última Vacante."""
import os, sys
for line in open(".env"):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip()

sys.path.insert(0, "factory/skills/internos/dashboard_updater")
from service import DashboardUpdaterService

instruccion = """
Agrega una seccion llamada "Ultima Vacante" al sidebar st.radio y crea su bloque elif.

Esta seccion debe:

1. Cargar la vacante mas reciente con funcion @st.cache_data(ttl=30):
   def _ultima_vacante(): return select("vacantes", "select=*&order=created_at.desc&limit=1")

2. Card superior con datos de la vacante:
   - Folio, Titulo, Estado (badge), Canal, Empresa ID, Tipo (seed/real), Fecha creacion
   - st.expander("Ver descripcion") si tiene descripcion
   - st.expander("Ver requisitos") si tiene requisitos (es dict/jsonb)

3. Cuatro tabs debajo con todos los candidatos de esa vacante:

Tab "Candidatos":
   - Funcion: _candidatos_vacante(vid) = select("candidatos", f"select=*&vacante_id=eq.{vid}")
   - Funcion: _scores_vacante(vid) = select("scores", f"select=*&vacante_id=eq.{vid}")
   - Hacer map de scores por candidato_id
   - Tabla con pandas: Folio, Nombre, Telefono, Canal, Estado, Score, Pasa KO (checkmark o x), Creado

Tab "Pipeline":
   - Funcion: _pipeline_vacante(vid) = select("pipeline", f"select=*&vacante_id=eq.{vid}&order=created_at.desc")
   - Hacer map de candidatos por id para mostrar nombre
   - Tabla: Candidato (folio), Nombre, Etapa (badge), Notas, Fecha

Tab "Analisis AI":
   - Reusar _scores_vacante(vid) y _candidatos_vacante(vid)
   - Por cada candidato que tenga scores con campo detalle no vacio:
     * Mostrar st.subheader con nombre del candidato
     * Iterar sobre claves del detalle (dimension_maquinaria, dimension_compromiso, shift_zone_validator, retention_predictor, etc.)
     * Por cada clave mostrar nombre en negrita y campos: score/score_retencion, nivel/riesgo, recomendacion, resumen, senales como lista
     * Usar st.success si recomendacion=contratar, st.warning si revisar, st.error si descartar
   - Si no hay analisis: st.info("Sin analisis AI para esta vacante")

Tab "Respuestas":
   - Funcion: _respuestas_vacante(vid) = select("respuestas", f"select=*&vacante_id=eq.{vid}&order=candidato_id,orden")
   - Agrupar por candidato_id
   - Por cada candidato: st.expander con nombre (del map de candidatos) mostrando pregunta -> respuesta

4. Boton pequeno "Recargar" al inicio que llama st.cache_data.clear() y st.rerun()

5. Si no hay vacante: st.info("No hay vacantes registradas")

Mantener el mismo estilo oscuro, helpers _badge y _folio existentes, import pandas dentro de bloques.
"""

result = DashboardUpdaterService().ejecutar({
    "instruccion":      instruccion,
    "app_path":         "dashboard/app.py",
    "incluir_registry": False,
    "incluir_tablas":   True,
    "dry_run":          False,
})

if result["ok"]:
    print("OK")
    for c in result["data"].get("cambios", []):
        print(" -", c)
    print("Lineas:", result["data"]["lineas"])
else:
    print("ERROR:", result["error"])
