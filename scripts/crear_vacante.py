"""Crea una vacante con cuestionario usando Anthropic y la inserta en Supabase."""
import json, os, sys, urllib.request
from pathlib import Path

# Cargar .env
for line in (Path(__file__).parent.parent / ".env").read_text(encoding="utf-8").splitlines():
    raw = line.strip()
    if not raw or raw.startswith("#") or "=" not in raw:
        continue
    k, v = raw.split("=", 1)
    k = k.strip(); v = v.strip().strip('"').strip("'")
    if k and k not in os.environ:
        os.environ[k] = v

sys.path.insert(0, str(Path(__file__).parent.parent))
from factory.engine import SupabaseClient

EMPRESA_ID  = os.getenv("RH_EMPRESA_ID", "rh_empresa_1")
ANTHROPIC_KEY = os.environ["ANTHROPIC_API_KEY"]

PUESTO      = "Chofer de Tórtón"
SECTOR      = "logística"
UBICACION   = "Mérida, Yucatán, México"
PROFUNDIDAD = "medio"
N_PREGUNTAS = 10

prompt = f"""
Puesto: {PUESTO}
Ubicación: {UBICACION}
Sector: {SECTOR}

Genera en JSON:
{{
  "titulo": "{PUESTO} — {UBICACION}",
  "descripcion": "descripción del puesto de 2-3 líneas",
  "requisitos": {{
    "reglas_knockout": [
      {{"campo": "licencia", "debe_contener": "tipo E o superior"}},
      {{"campo": "experiencia", "debe_contener": "mínimo 2 años en tórtón"}}
    ],
    "criterios_scoring": [
      "años de experiencia en vehículos de carga pesada",
      "conocimiento de rutas en Yucatán y sureste de México",
      "disponibilidad para viajes foráneos",
      "referencias laborales verificables",
      "historial limpio en licencia"
    ]
  }},
  "preguntas": [
    "¿Cuál es tu nombre completo?",
    "¿Cuál es tu número de teléfono?",
    "¿Tienes licencia tipo E o federal?",
    "¿Cuántos años llevas manejando tórtón o vehículo de carga similar?",
    "¿Has trabajado en rutas dentro de Yucatán o el sureste del país?",
    "¿Tienes disponibilidad para viajes foráneos de 1 a 3 días?",
    "¿En qué empresa trabajaste más recientemente y cuánto tiempo estuviste?",
    "¿Tienes alguna infracción grave o accidente en los últimos 3 años?",
    "¿Cuál es tu expectativa de sueldo mensual?",
    "¿Cuándo puedes iniciar?"
  ]
}}
Solo JSON válido, sin bloques de código.
"""

payload = {
    "model": "claude-haiku-4-5-20251001",
    "max_tokens": 1024,
    "system": "Eres experto en RH. Generas vacantes realistas. Solo JSON válido.",
    "messages": [{"role": "user", "content": prompt}],
}
req = urllib.request.Request(
    "https://api.anthropic.com/v1/messages",
    data=json.dumps(payload).encode(),
    headers={"content-type": "application/json", "x-api-key": ANTHROPIC_KEY, "anthropic-version": "2023-06-01"},
    method="POST",
)
with urllib.request.urlopen(req, timeout=60) as r:
    result = json.loads(r.read())
raw = result["content"][0]["text"].strip()
if raw.startswith("```"):
    raw = raw.split("\n", 1)[-1]
    if raw.endswith("```"):
        raw = raw[:-3]
data = json.loads(raw.strip())

print(f"Vacante generada: {data['titulo']}")
print(f"Preguntas: {len(data['preguntas'])}")

db = SupabaseClient({})

v_row = db.rest_insert("vacantes", {
    "empresa_id":  EMPRESA_ID,
    "titulo":      data["titulo"],
    "descripcion": data["descripcion"],
    "requisitos":  data["requisitos"],
    "canal":       "telegram",
    "estado":      "activa",
    "tipo":        "real",
})
if not v_row.get("ok"):
    print("ERROR vacante:", v_row.get("error"))
    sys.exit(1)

v_data     = v_row["data"][0] if isinstance(v_row["data"], list) else v_row["data"]
vacante_id = v_data["id"]
folio      = v_data.get("folio", "?")
print(f"Vacante insertada: {folio} — id: {vacante_id}")

q_row = db.rest_insert("cuestionarios", {
    "empresa_id":  EMPRESA_ID,
    "vacante_id":  vacante_id,
    "puesto":      data["titulo"],
    "profundidad": PROFUNDIDAD,
    "canal":       "telegram",
    "preguntas":   data["preguntas"],
})
if q_row.get("ok"):
    print(f"Cuestionario insertado con {len(data['preguntas'])} preguntas")
else:
    print("ERROR cuestionario:", q_row.get("error"))

print(f"\n✓ Listo. Vacante {folio} creada.")
print(f"  ID: {vacante_id}")
print(f"  Preguntas: {data['preguntas'][:2]} ...")
