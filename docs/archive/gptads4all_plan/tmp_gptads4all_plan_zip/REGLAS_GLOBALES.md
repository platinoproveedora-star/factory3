REGLAS GLOBALES v1.3 — COPIAR AL INICIO DE CADA BRIEF HERMES
(GPTAds4All / Factory3)

1. Tu carpeta de trabajo EXCLUSIVA:
   factory/skills/internos/vertical_gptads4all/{tus_skills}/
   NO tocas ninguna otra carpeta de skill.

2. PROHIBIDO tocar (ni leer-modificar-guardar):
   - factory/skills/registry.json
   - factory/agents/registry.json
   - factory/engine/ (nada)
   - factory_api.py
   - .env
   - CLAUDE.md
   - Skills de otros agentes

3. Contratos: lee CONTRACTS.md ANTES de escribir código.
   Tu input y output son EXACTAMENTE los dicts ahí definidos.
   ProductRef solo lo consume product_brief_build;
   todos los demás consumen ProductBrief.
   Presupuesto: daily_budget_amount + currency (default "MXN").
   Si crees que el contrato está mal, NO lo cambies — repórtalo.

4. Estructura obligatoria por skill:
   {skill_name}/manifest.json + skill.py + service.py
   skill.py: def run(context: dict) -> dict
   Output: {"ok": true, "data": {...}} | {"ok": false, "error": "..."}
   Sin excepciones al caller — todo error es dict.

5. DB solo con: from factory.engine import SupabaseClient
   Schema lógico: gptads4all — se pasa via context["schema"] = "gptads4all"
   (SupabaseClient lo manda como header Accept-Profile/Content-Profile).
   NUNCA escribir el schema en el nombre de tabla:
     CORRECTO:   db.rest_insert("campaigns", row)   con context["schema"]="gptads4all"
     INCORRECTO: db.rest_insert("gptads4all.campaigns", row)
   Todo filtrado por empresa_id.
   dry_run default True si escribes a DB o disco.

6. IA solo con: anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
   Modelo: claude-haiku-4-5 salvo que el brief diga otra cosa.
   Singleton global (_CLIENT pattern).

7. NO hardcodear productos, clientes, ni empresas.
   Prueba con: empresa_id=EMP_DEMO, product_key=prod_demo_001.

8. Manifest mínimo:
   {"type":"skill","name":"...","version":"0.1.0","kind":"executable",
    "entrypoint":"skill.py","description":"...","requires_env":[...]}

9. Criterio de TERMINADO: tu skill corre con el context de ejemplo
   del CONTRACTS.md y devuelve el contrato de output exacto.

10. CONTRACTS.md es SOLO LECTURA para agentes 1-6 y 10.
    Únicamente Hermes 8 (integrador) puede editarlo, y solo con
    aprobación de Ach. Si detectas un problema en un contrato,
    repórtalo — no lo corrijas tú.

11. Solo Hermes 8 crea/modifica CONTRACTS.md y SCHEMA.sql.
    Cualquier otro agente que detecte un problema en ellos lo REPORTA.

12. IDs (intent_id, hint_id, creative_id, variant) se generan en
    código Python de forma secuencial — la IA NUNCA genera IDs.
