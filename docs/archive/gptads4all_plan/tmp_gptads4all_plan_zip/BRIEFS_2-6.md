BRIEFS HERMES 2-6 — GPTAds4All v1.3 (FINALES, aprobados)
[Pegar REGLAS GLOBALES v1.3 arriba de cada brief]

═══════════════════════════════════════════
=== HERMES 2 — gptads_intent_research ===
═══════════════════════════════════════════
Carpeta: factory/skills/internos/vertical_gptads4all/gptads_intent_research/
Input: ProductBrief (context["product_brief"], contrato exacto)

Tarea:
Con IA (Haiku) generar intenciones CONVERSACIONALES que un usuario
de ChatGPT expresaría relacionadas al producto.
- NO keywords SEO. NO listas tipo Google Ads.
- max_intents validado en código: mín 5, máx 15, default 10
  (context.get("max_intents", 10), clamp en Python)
- intent_type SOLO: informacional | comparacion | compra
- funnel_stage SOLO: awareness | consideration | decision
- priority: int 1-5 (1 = máxima)
- intent_id lo genera PYTHON secuencial: int_001, int_002...
  La IA NO genera IDs.
- Prompt pide JSON puro; 1 reintento si no parsea.
- Validar que product_key exista en el input.

Output: {"ok":true,"data":{"intent_set": IntentSet, "warnings":[...]}}
Errores:
- {"ok":false,"error":"ai_response_not_parseable"} (tras reintento)
- {"ok":false,"error":"product_key required"}
Restricciones: NO DB. NO SupabaseClient. NO archivos.

═══════════════════════════════════════════
=== HERMES 3 — gptads_context_hints_generate ===
═══════════════════════════════════════════
Carpeta: factory/skills/internos/vertical_gptads4all/gptads_context_hints_generate/
Input: ProductBrief + IntentSet (context["product_brief"], context["intent_set"])

Tarea:
Por cada intent, generar context hints con IA (Haiku).
- El núcleo es hint_text: describe SEÑAL/CONTEXTO CONVERSACIONAL.
  trigger_keywords es metadata auxiliar.
- CORRECTO:  "El usuario habla de necesitar inglés para una entrevista laboral"
  INCORRECTO: "curso inglés entrevista trabajo"
- hints_per_intent: mín 1, máx 3, default 2 (clamp en código)
- hint_id lo genera PYTHON: hint_001, hint_002... La IA NO genera IDs.
- Cada hint DEBE referenciar un intent_id real del IntentSet recibido.
- Si IA devuelve intent_id inexistente: rechazar y 1 reintento.
- trigger_keywords: máx 5 por hint, strings simples, sin duplicados.
- priority: int 1-5 (1 = máxima).

Output: {"ok":true,"data":{"context_hint_set": ContextHintSet, "warnings":[...]}}
Errores:
- {"ok":false,"error":"invalid_intent_reference"} (tras reintento)
- {"ok":false,"error":"ai_response_not_parseable"}
Restricciones: NO DB. NO SupabaseClient. NO archivos.

═══════════════════════════════════════════
=== HERMES 4 — gptads_campaign_build ===
═══════════════════════════════════════════
Carpeta: factory/skills/internos/vertical_gptads4all/gptads_campaign_build/
Input: ProductBrief + IntentSet + ContextHintSet

Tarea (SIN IA — puro código determinista):
Construir CampaignDraft (contrato v1.3 — daily_budget_mxn NO EXISTE):
{
  "empresa_id", "product_key",
  "campaign_key": "camp_{product_key}_{YYYYMMDDHHMMSS}",
  "campaign_name": determinista de product_name + market (NO IA),
  "objective": "conversions" | "traffic" | "leads" (default conversions),
  "daily_budget_amount": de context o default 500,
  "currency": ISO 4217 uppercase,
  "status": "draft",
  "intent_ids": [...], "hint_ids": [...]
}
Currency:
- Si no viene en context, inferir con mapa determinista: MX→MXN, US→USD.
- País desconocido y sin currency en context:
  {"ok":false,"error":"currency_required"}
Validaciones:
- Todos los intent_ids existen en IntentSet.
- Todos los hint_ids existen en ContextHintSet.
Persistencia:
- dry_run default True. dry_run=True: CERO SupabaseClient, cero writes.
- dry_run=False: SOLO SupabaseClient(context), schema via
  context["schema"]="gptads4all". Upsert products, intents,
  context_hints, campaigns — siempre identificado por empresa_id.
- Si falla: {"ok":false,"error":"db_persistence_failed"}

Output: {"ok":true,"data":{"campaign_draft": CampaignDraft, "warnings":[...]}}

═══════════════════════════════════════════
=== HERMES 5 — gptads_creative_generate ===
═══════════════════════════════════════════
Carpeta: factory/skills/internos/vertical_gptads4all/gptads_creative_generate/
Input: CampaignDraft + ProductBrief + IntentSet + ContextHintSet

Tarea:
Por cada intent, generar copies con IA (Haiku) usando
ProductBrief.value_props y ProductBrief.tone.
- variants_per_intent: mín 2, máx 3, default 2 (clamp en código)
- La IA NO genera creative_id ni variant — Python los asigna:
  creative_id: cre_001, cre_002... / variant: contador por intent 1,2,3
- Longitudes: headline ≤60, body ≤200, cta ≤25 chars
- NO truncar silenciosamente como primera opción. Flujo:
  IA genera → Python valida → si excede, 1 reintento pidiendo
  corrección → si vuelve a exceder, truncar seguro + warning.
- Cada creative referencia un intent_id real.
- La IA NO debe inventar: precio, descuentos, certificaciones,
  garantías, disponibilidad, claims no presentes en ProductBrief.
- Agregar al prompt literal:
  "Do not invent commercial claims or product facts."
Persistencia:
- dry_run default True (no DB).
- dry_run=False: upsert creatives con SupabaseClient(context).
Errores:
- {"ok":false,"error":"ai_response_not_parseable"} (tras reintento)
- {"ok":false,"error":"db_persistence_failed"}

Output: {"ok":true,"data":{"creative_set": CreativeSet, "warnings":[...]}}

═══════════════════════════════════════════
=== HERMES 6 — gptads_bulk_export ===
═══════════════════════════════════════════
Carpeta: factory/skills/internos/vertical_gptads4all/gptads_bulk_export/
Input: CampaignDraft + CreativeSet + IntentSet + ContextHintSet

Tarea:
Exportar la campaña completa. format: "csv" | "json" | "both"
(default csv). Contrato ExportArtifact v1.3 con artifacts[].

Columnas CSV mínimas (una fila por creative, SIN perder relación
con hints):
  campaign_key, campaign_name, product_key,
  intent_id, intent_text,
  hint_ids, hint_texts,          ← serializados con "|"
  creative_id, variant, headline, body, cta

JSON: conservar estructura completa (anidada) — NO aplanar al CSV.

dry_run (default True):
- dry_run=True: generar contenido EN MEMORIA, validar rows_exported,
  devolver file_path=null en cada artifact,
  warning "dry_run_no_file_written". NO escribir archivo. NO DB.
- dry_run=False: crear output_dir si no existe
  (default /tmp/gptads_exports, configurable via
  context.get("output_dir")), escribir archivo(s),
  insert en gptads4all.exports.
- Sanitizar campaign_key antes de usarlo en filename
  (solo [a-z0-9_-]) — evitar path traversal.

Solo stdlib: csv, json, pathlib, datetime. SIN pandas.

Errores:
- {"ok":false,"error":"file_write_failed"}
- Si DB falla DESPUÉS de crear archivo: NO borrar el archivo;
  {"ok":false,"error":"db_persistence_failed"} y reportar
  file_path en warnings.

Output: {"ok":true,"data":{"export_artifact": ExportArtifact, "warnings":[...]}}
