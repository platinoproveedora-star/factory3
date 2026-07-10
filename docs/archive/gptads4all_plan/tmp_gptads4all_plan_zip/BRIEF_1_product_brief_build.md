=== HERMES 1 — gptads_product_brief_build === (v FINAL, aprobado)
[Pegar REGLAS GLOBALES v1.2 arriba de este brief]

Carpeta:
factory/skills/internos/vertical_gptads4all/gptads_product_brief_build/

Input:
ProductRef crudo desde context (ver CONTRACTS.md).

Tarea:
Transformar ProductRef en ProductBrief con IA (Haiku):
- completar description si falta
- inferir category si falta
- validar market
- normalizar market.language a formato es-MX / en-US si es posible
- generar value_props: exactamente 3 propuestas de valor
- asignar tone: "profesional" | "casual" | "urgente"
  Si tone no puede inferirse claramente, usar "profesional" (default).
  Nunca inventar un valor fuera de ese enum.
- NO inventar price_range ni url; si faltan, dejarlos null
- Prompt debe pedir JSON puro; parsear con try/except

Output (contrato ProductBrief de CONTRACTS.md):
{"ok":true,"data":{"product_brief": ProductBrief, "warnings":[...]}}

warnings lista qué campos fueron inferidos/completados por IA
(vacía si todo venía en el input).

Errores:
Si falta empresa_id o product_name:
{"ok":false,"error":"empresa_id and product_name are required"}
Si la IA no devuelve JSON parseable tras 1 reintento:
{"ok":false,"error":"ai_response_not_parseable"}

Restricciones duras:
- No escribe a DB.
- No debe llamar SupabaseClient (ni para leer).
- No debe crear archivos.
