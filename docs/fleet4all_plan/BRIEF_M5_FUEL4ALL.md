=== BRIEF MÓDULO 5 — FUEL4ALL (vertical_fleet4all_fuel) ===
[Pegar 00_REGLAS_GLOBALES_FLEET4ALL.md arriba]
Contratos: FuelLoadInput/FuelLoad, EfficiencyReport.

SKILLS (3):
1. fuel_load_capture — texto o foto (Haiku vision extrae liters,
   amount, load_date, station; usuario confirma). Folio F-NNNN.
   price_per_liter = amount/liters en Python (div/0 protegido).
   odometer_km: si viene, actualiza units.odometer_km si es mayor
   al actual (nunca retrocede; menor → warning "odometer_lower").
   Opcional: registrar también como expense (context["as_expense"]
   =true → llama expense_capture via SkillRunner, type=fuel).
2. mileage_calculate — por unit y periodo: km_traveled =
   delta odómetros de fuel_loads ordenados por fecha,
   liters_loaded = suma, km_per_liter = división protegida.
   expected_km_per_liter de context o promedio histórico de la
   unidad (mínimo 3 periodos; si no hay, flag=ok con warning
   "no_baseline"). deviation_pct y flag por reglas del contrato.
   Upsert a fleet4all.fuel_efficiency.
3. deviation_alert — read-only sobre fuel_efficiency: unidades en
   warning/alert del último periodo, con redacción del mensaje de
   alerta (Haiku, solo redacción — los números ya vienen
   calculados). dry_run devuelve mensajes sin enviar.

ERRORES: unit_not_found | insufficient_data |
ai_response_not_parseable | db_persistence_failed
TERMINADO: capture→mileage→alert corre con EMP_DEMO_FLEET y 4
cargas dummy; detecta desviación sembrada de -25%.
