REGLAS GLOBALES FLEET4ALL v1 — COPIAR AL INICIO DE CADA BRIEF
(vertical fleet4all / Factory3)

1. Carpeta EXCLUSIVA por agente:
   factory/skills/internos/vertical_fleet4all_{modulo}/{skill}/
2. PROHIBIDO: factory/skills/registry.json, factory/agents/registry.json,
   factory/engine/, factory_api.py, .env, CLAUDE.md, skills ajenos.
   Solo el INTEGRADOR toca registry, CONTRACTS y SCHEMA.
3. Contratos: leer 01_CONTRACTS_FLEET4ALL.md antes de codificar.
   Input/output EXACTOS. Problema en contrato → reportar, no corregir.
4. Estructura por skill: manifest.json + skill.py + service.py
   skill.py: def run(context: dict) -> dict
   Output: {"ok":true,"data":{...}} | {"ok":false,"error":"..."}
   Sin excepciones al caller.
5. DB: SOLO from factory.engine import SupabaseClient.
   context["schema"]="fleet4all". NUNCA schema en nombre de tabla.
   Todo filtrado por empresa_id. dry_run default True al escribir.
   Exponer schema SOLO con skill supabase_expose_schema (jamás ALTER manual).
6. IA: anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"]),
   claude-haiku-4-5, singleton _CLIENT. Vision solo donde el brief lo pide.
7. CERO hardcodeo de empresas/clientes (adiós DEFAULT 'LOGPLAT').
   Prueba con empresa_id=EMP_DEMO_FLEET.
8. Folios: {PREFIJO}-{NNNN} secuencial POR EMPRESA (nunca global).
   Los genera Python, nunca la IA ni el usuario.
9. Montos calculados (trip_profit, balance, settlement_total,
   efficiency) SIEMPRE en código. Nunca capturados ni generados por IA.
10. currency en toda tabla/contrato de dinero. Default "MXN",
    jamás moneda en nombres de campos.
11. Bilingüe: mensajes al usuario final según context["language"]
    ("es" default | "en"). Textos en dict MESSAGES = {"es":{...},"en":{...}}.
12. Terminado = el skill corre con el context de ejemplo del
    CONTRACTS y devuelve el contrato exacto.
