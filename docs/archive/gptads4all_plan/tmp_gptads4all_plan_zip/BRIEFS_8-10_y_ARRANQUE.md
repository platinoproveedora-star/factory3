BRIEFS HERMES 8 y 10 + ORDEN DE ARRANQUE — GPTAds4All v1.3 (FINAL)

═══════════════════════════════════════════
=== HERMES 8 — INTEGRADOR ===
═══════════════════════════════════════════
[REGLAS GLOBALES v1.3 — EXCEPCIÓN: tú SÍ tocas registry.json,
CONTRACTS.md y SCHEMA.sql]

FASE A (antes que todos):
1. Crear factory/skills/internos/vertical_gptads4all/
2. Crear CONTRACTS.md v1.3 (contenido dado por Ach).
3. Crear SCHEMA.sql v1.2 (contenido dado por Ach). NO EJECUTAR.
4. Verificar antes de liberar:
   - daily_budget_mxn NO existe en ningún documento
   - CampaignDraft usa daily_budget_amount + currency
   - ExportArtifact usa artifacts[]
   - Keys envolventes documentadas (product_brief, intent_set,
     context_hint_set, campaign_draft, creative_set, export_artifact)
5. Solo entonces confirmar a Ach: liberar Hermes 1-6 y Hermes 10.

FASE B (cuando 1-6 reporten TERMINADO):
1. Verificar estructura de cada skill:
   manifest.json + skill.py + service.py
2. Correr skill_manifest_validator sobre los 6.
3. Correr skill_input_output_eval sobre los 6.
4. Ejecutar skill_registry_sync — ÚNICO agente que escribe
   factory/skills/registry.json.
5. SMOKE TEST E2E con dry_run=true (context abajo).
6. Validar TODO:
   - cero excepciones en la cadena de 6 skills
   - contratos exactos, todas las keys presentes
   - ProductBrief: exactamente 3 value_props, tone en enum válido
   - >=5 intents, todos los intent_id formato int_NNN
   - >=1 hint por intent, todos los hint.intent_id válidos
   - >=2 creatives por intent, longitudes válidas (60/200/25)
   - rows_exported >= 10
   - file_path = null en todos los artifacts (dry_run)
   - warning "dry_run_no_file_written" presente
   - CERO writes a DB (verificable: ningún SupabaseClient llamado)
   - registry.json tiene las 6 entradas nuevas con key
     "vertical_gptads4all/{skill_name}"
7. TEST AISLADO adicional: gptads_bulk_export con dry_run=false.
   Validar que el archivo CSV real existe en /tmp/gptads_exports/
   y tiene las columnas mínimas del brief 6.
8. Si un skill falla: NO lo modificas. Reportas a Ach:
   skill, input usado, output recibido, contrato roto.
   Corrige el agente dueño.

SMOKE TEST — context inicial:
{
  "empresa_id": "EMP_DEMO",
  "product_key": "prod_demo_001",
  "product_name": "Curso de inglés online",
  "description": "Curso B2B para profesionales",
  "category": "educacion",
  "price_range": "500-1500 MXN",
  "market": {"country":"MX","language":"es",
             "audience":"profesionales 25-45"},
  "dry_run": true
}

═══════════════════════════════════════════
=== HERMES 10 — DOCUMENTACIÓN ===
═══════════════════════════════════════════
[REGLAS GLOBALES v1.3 arriba]

ARRANQUE: NO en minuto 0. Solo después de confirmación
Fase A de Hermes 8 (CONTRACTS.md v1.3 ya existe).

Solo puede crear/modificar:
factory/skills/internos/vertical_gptads4all/README.md

Tarea:
- Leer CONTRACTS.md como fuente de verdad. NO inventar campos.
- NO duplicar contratos completos — referenciar CONTRACTS.md.
- Pipeline (diagrama texto):
  ProductRef → ProductBrief → IntentSet → ContextHintSet
  → CampaignDraft → CreativeSet → ExportArtifact
- Ejemplos de ejecución: deben respetar el patrón REAL de /run/
  del repo (POST /run/{skill_name} con Bearer FACTORY_RUN_SECRET).
  Si no puede confirmar el curl real leyendo código permitido:
  OMITIR curl y documentar solo ejecución Python con SkillRunner.
- Variables de entorno requeridas por skill (de los manifests).
- Roadmap v1.1 (Ola 2): advertiser_audit, adgroup_build,
  landing_generate, platform_validate, metrics_ingest,
  experiment_score.

═══════════════════════════════════════════
ORDEN DE ARRANQUE
═══════════════════════════════════════════
T0:  Hermes 8 Fase A (carpeta + CONTRACTS.md v1.3 + SCHEMA.sql)
T1:  Confirmación Fase A → liberar Hermes 1,2,3,4,5,6 y 10
     en paralelo (carpetas aisladas)
T2:  1-6 reportan TERMINADO → Hermes 8 Fase B
     (validators + registry + smoke test dry_run=true)
T3:  Test aislado bulk_export dry_run=false (archivo real)
T4:  Verde total → reporte a Ach → OLA 2

OLA 2 (solo después de T4 verde):
advertiser_audit, adgroup_build, landing_generate,
platform_validate, metrics_ingest, experiment_score
— briefs contra contratos ya validados en la realidad.
