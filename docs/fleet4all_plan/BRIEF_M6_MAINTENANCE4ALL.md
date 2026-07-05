=== BRIEF MÓDULO 6 — MAINTENANCE4ALL (vertical_fleet4all_maintenance) ===
[Pegar 00_REGLAS_GLOBALES_FLEET4ALL.md arriba]
Contratos: MaintenancePlan, Service, PartMovement.
Referencia PERMITIDA (lectura): vertical_erp_inventory (kardex
de Duralón) para el patrón de movimientos.

SKILLS (4):
1. maintenance_schedule — CRUD de planes (M-NNNN). next_due_km =
   last_service_km + every_km; next_due_date = last_service_date +
   every_days (Python). Read con context["due_soon"]=true devuelve
   planes a <=1000 km o <=15 días de vencer (umbral configurable).
2. service_capture — registra servicio (SV-NNNN); si trae
   plan_folio actualiza last_service_* y recalcula next_due_*;
   si trae odometer_km actualiza units (regla nunca-retrocede).
   Costo opcionalmente registrable como expense
   (context["as_expense"]=true, type=repair).
3. parts_kardex — alta de parts + movimientos in/out (MV-NNNN).
   stock = stock ± quantity; out > stock →
   {"ok":false,"error":"insufficient_stock"}. avg_cost recalculado
   en entradas (promedio ponderado, Python). Alerta bajo mínimo
   en warnings.
4. unit_record — read-only: expediente de la unidad — datos,
   odómetro, historial de servicios, planes activos, próximos
   vencimientos, costo de mantenimiento acumulado por periodo.

ERRORES: unit_not_found | plan_not_found | part_not_found |
insufficient_stock | db_persistence_failed
TERMINADO: plan→service→kardex→record corre con EMP_DEMO_FLEET;
next_due recalcula bien tras un service.
