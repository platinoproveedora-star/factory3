FLEET4ALL — INTEGRADOR Y ORDEN DE ARRANQUE v1

═══════════════════════════════════════
BRIEF INTEGRADOR (mismo rol que Hermes 8 en GPTAds4All)
═══════════════════════════════════════
[REGLAS GLOBALES — EXCEPCIÓN: tú SÍ tocas registry.json,
CONTRACTS y SCHEMA del vertical]

FASE A (antes de todos):
1. Crear factory/skills/internos/vertical_fleet4all_trips/ ...
   (solo carpetas de la ola activa)
2. Copiar a docs/fleet4all_plan/: los 3 docs maestros
   (00_REGLAS, 01_CONTRACTS, 02_SCHEMA) — fuente de verdad.
3. NO ejecutar 02_SCHEMA_FLEET4ALL.sql. Cuando Ach apruebe:
   correr SQL en Supabase y exponer con supabase_expose_schema
   {"schema":"fleet4all","dry_run":false}.
4. Verificar: cero DEFAULT de empresa hardcodeado en schema,
   currency en toda tabla de dinero, updated_at en todas.
5. Liberar agentes de la ola activa.

FASE B (cuando la ola reporte TERMINADO):
1. Estructura por skill (manifest+skill.py+service.py).
2. skill_manifest_validator + skill_input_output_eval.
3. skill_registry_sync (ÚNICO que escribe registry.json).
4. Smoke test de la ola (abajo). Falla → reporta, NO parcha.

═══════════════════════════════════════
OLAS DE PRODUCCIÓN
═══════════════════════════════════════
OLA F1 (ahora): M1 Trips + M2 Collections — 2 agentes + integrador.
  Es LOGPLAT partido en dos: menor riesgo, mayor reuso.
  SMOKE F1 (EMP_DEMO_FLEET, dry_run=true):
  trip_create → 3x expense_capture (1 por foto dummy) →
  trip_close (profit correcto) → payment_capture parcial →
  receivables_sync (status=partial) → payment resto (paid) →
  statement_generate → collection_reminder sobre un trip
  overdue sembrado. Sync corrido 2 veces = idéntico (idempotencia).

OLA F2: M3 CartaPorte + M4 Settlements — el gancho de venta al
  gremio + la retención. Prerreq M3: sandbox PAC activo.
  SMOKE F2: cartaporte build→validate→stamp(sandbox)→uuid;
  advance→settlement_calculate→approve→receipt.

OLA F3: M5 Fuel + M6 Maintenance + M7 Quotes — 3 agentes paralelos.
  SMOKE F3: fuel con desviación sembrada detectada; plan→service→
  kardex sin stock negativo; rate→quote→accept crea trip.

OLA F4 (cuando M1-M3 tengan usuarios reales): M8 Loads.
  SMOKE F4: flujo dos-empresas completo.

MIGRACIÓN PLATINO (tras smoke F1 verde):
Script logplat.* → fleet4all.* (traducción de columnas, folios
conservados, empresa_id=EMP_LOGPLAT). Platino Logística = tenant #1
y validación en producción real antes del piloto del gremio.

PARALELO NO-HERMES (Ach + Claude):
- Alta de EMP_FLEET4ALL en companies/ (company.json, pattern)
- Integración al portal Apps4all (grants por módulo — patrón
  Conta4all) y al marketplace en construcción
- Pricing por módulo/suite para la propuesta al socio del gremio
