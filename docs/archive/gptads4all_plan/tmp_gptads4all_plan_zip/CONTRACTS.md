# GPTAds4All — CONTRATOS DE DATOS v1.3
# Todo viaja como dict en context. Ningún skill importa clases de otro skill.
# Si un campo no aplica, va como null — nunca se omite la key.

## ProductRef (input crudo del pipeline — lo que mete el usuario)
{
  "empresa_id": "EMP_DEMO",
  "product_key": "prod_demo_001",
  "product_name": "Curso de inglés online",
  "description": "Curso de inglés B2B para profesionales",
  "category": "educacion",
  "price_range": "500-1500 MXN",
  "url": null,
  "market": {
    "country": "MX",
    "language": "es",
    "audience": "profesionales 25-45"
  }
}

## ProductBrief (output de gptads_product_brief_build — normalizado y enriquecido)
{
  "empresa_id": "EMP_DEMO",
  "product_key": "prod_demo_001",
  "product_name": "Curso de inglés online",
  "description": "completada/enriquecida por IA si venía incompleta",
  "category": "inferida si faltaba",
  "price_range": "500-1500 MXN",
  "market": {"country":"MX","language":"es","audience":"profesionales 25-45"},
  "value_props": ["prop 1", "prop 2", "prop 3"],
  "tone": "profesional | casual | urgente"
}

## IntentSet (output de gptads_intent_research)
{
  "product_key": "prod_demo_001",
  "intents": [
    {
      "intent_id": "int_001",
      "intent_text": "quiero aprender inglés para mi trabajo",
      "intent_type": "informacional | comparacion | compra",
      "funnel_stage": "awareness | consideration | decision",
      "priority": 1
    }
  ]
}

## ContextHintSet (output de gptads_context_hints_generate)
{
  "product_key": "prod_demo_001",
  "hints": [
    {
      "hint_id": "hint_001",
      "intent_id": "int_001",
      "hint_text": "usuario menciona crecimiento profesional o entrevistas en inglés",
      "trigger_keywords": ["trabajo", "entrevista", "carrera"],
      "priority": 1
    }
  ]
}

## CampaignDraft (output de gptads_campaign_build)
{
  "empresa_id": "EMP_DEMO",
  "product_key": "prod_demo_001",
  "campaign_key": "camp_demo_001",
  "campaign_name": "Curso Inglés B2B — MX — Q3",
  "objective": "conversions",
  "daily_budget_amount": 500,
  "currency": "MXN",
  "status": "draft",
  "intent_ids": ["int_001"],
  "hint_ids": ["hint_001"]
}

## CreativeSet (output de gptads_creative_generate)
{
  "campaign_key": "camp_demo_001",
  "creatives": [
    {
      "creative_id": "cre_001",
      "intent_id": "int_001",
      "headline": "max 60 chars",
      "body": "max 200 chars",
      "cta": "max 25 chars",
      "variant": 1
    }
  ]
}

## ExportArtifact (output de gptads_bulk_export)
{
  "campaign_key": "camp_demo_001",
  "format": "csv | json | both",
  "artifacts": [
    {
      "format": "csv",
      "file_path": "ruta o null si dry_run",
      "rows_exported": 12
    }
  ],
  "generated_at": "ISO 8601"
}
# Con format=both, artifacts trae 2 entradas (csv y json).
# Con dry_run=true: file_path=null y warning "dry_run_no_file_written".

## REGLA UNIVERSAL:
# - Input de cada skill = output del anterior + empresa_id siempre presente
# - ProductRef SOLO lo consume gptads_product_brief_build.
#   Todo lo demás consume ProductBrief.
# - Output SIEMPRE: {"ok": true, "data": {CONTRATO}} o {"ok": false, "error": "..."}
# - IDs: snake_case con prefijo (int_, hint_, camp_, cre_)
# - dry_run default True en skills que escriben a DB o disco
# - Presupuesto: daily_budget_amount + currency (default "MXN") —
#   nunca hardcodear moneda en nombres de campos
# - Keys envolventes en data (obligatorias):
#   product_brief_build → data.product_brief
#   intent_research → data.intent_set
#   context_hints_generate → data.context_hint_set
#   campaign_build → data.campaign_draft
#   creative_generate → data.creative_set
#   bulk_export → data.export_artifact
#   Todas pueden incluir data.warnings (lista, puede ir vacía)
# - IDs (intent_id, hint_id, creative_id, variant) los genera PYTHON,
#   nunca la IA
# - Solo Hermes 8 crea/modifica CONTRACTS.md y SCHEMA.sql
