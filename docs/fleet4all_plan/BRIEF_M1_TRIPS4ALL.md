=== BRIEF MÓDULO 1 — TRIPS4ALL (vertical_fleet4all_trips) ===
[Pegar 00_REGLAS_GLOBALES_FLEET4ALL.md arriba]
Contratos: TripInput/Trip, ExpenseInput/Expense (01_CONTRACTS).
Base de referencia PERMITIDA (solo lectura, para clonar lógica):
EMP_LOGPLAT/ (bot_mode.py, service.py) y
vertical_emp_logplat/emp_logplat_message_handler.

SKILLS (5):
1. trip_create — crea trip; trip_folio T-NNNN secuencial por empresa
   (query max folio de la empresa + 1, en Python). Valida
   empresa_id, customer u origin/destination presentes.
   dry_run default True; write: insert fleet4all.trips.
2. expense_capture — dos entradas: texto "500,fuel,05/07/26,T-0025"
   (parse en Python) o context["image_base64"] → Haiku vision extrae
   {amount,concept,expense_date} → devuelve draft para confirmación
   (context["confirmed"]=true persiste). expense_type inferido de
   concept por dict de keywords (fuel: gasolina/diesel; tolls:
   caseta/peaje...) — determinista, no IA. Folio G-NNNN.
   Si trae trip_folio: validar que exista y esté active.
3. trip_close — recalcula trip_cost = sum(expenses del trip),
   trip_profit = sale_price - trip_cost, status=closed.
   Idempotente. NUNCA acepta profit manual. Si trip ya closed:
   re-cálculo permitido con warning "recalculated".
4. trip_kpis — read-only: utilidad semanal/mensual, trips activos,
   profit por unit_key y por driver_key, top gastos por tipo.
   Input: empresa_id + period opcional. Exponible via GET /data/.
5. fleet_message_handler — bot canal-agnostic (clon del patrón
   emp_logplat_message_handler): estados en public.bot_states con
   chat_id=fleet4all_{empresa_id}_{from_phone}. Comandos: trip/viaje,
   expense/gasto, help/ayuda. Bilingüe por MESSAGES dict.
   Multi-tenant: resuelve empresa_id por from_phone contra tabla
   de registro (context["phone_registry"] o fleet4all.drivers.phone).

ERRORES: trip_not_found | trip_not_active | invalid_amount |
ai_response_not_parseable | db_persistence_failed
TERMINADO: los 5 corren con EMP_DEMO_FLEET y contratos exactos;
handler responde en es y en.
