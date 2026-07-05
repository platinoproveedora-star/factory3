# FLEET4ALL — CONTRATOS DE DATOS v1
# Todo viaja como dict en context. Keys envolventes obligatorias en data.
# Campos que no aplican van como null — nunca se omite la key.
# Folios: {PREFIJO}-{NNNN} secuencial POR EMPRESA, generados por Python.
# Prefijos: T (trips), G (expenses), P (payments), R (receivables),
#   CP (cartaporte), S (settlements), A (advances), F (fuel),
#   M (maintenance plans), SV (services), MV (part movements),
#   Q (quotes), L (loads), D (docs)

## TripInput → Trip (key: trip)
IN: { "empresa_id","customer","origin","destination","sale_price",
  "currency":"MXN","driver_key":null,"unit_key":null,
  "departure_date":"YYYY-MM-DD" }
OUT: IN + { "trip_folio":"T-0025","trip_cost":0,"trip_profit":0,
  "trip_status":"active","payment_status":"receivable" }

## ExpenseInput → Expense (key: expense)
IN: { "empresa_id","trip_folio":null,"amount","concept",
  "expense_type":"fuel|tolls|food|repair|other",
  "expense_date","driver_key":null,"doc_id":null }
Captura por foto: context["image_base64"] → IA vision extrae
{amount, concept, expense_date} → usuario confirma → Python folia.
OUT: IN + { "expense_folio":"G-0101" }

## PaymentInput → Payment (key: payment)
IN: { "empresa_id","trip_folio","amount","payment_date",
  "method":"transfer|cash|check|card","tracking_key":null,"notes":null }
OUT: IN + { "payment_folio":"P-0040" }
Efecto: dispara receivables_sync del trip.

## Receivable (key: receivable) — SIEMPRE calculado
{ "receivable_folio":"R-0025","trip_folio","customer",
  "total_amount","paid_amount","balance","currency",
  "trip_date","due_date",
  "collection_status":"pending|partial|paid|overdue" }
Reglas: paid>=total→paid; 0<paid<total→partial;
balance>0 y due_date<hoy→overdue.

## Statement (key: statement)
{ "empresa_id","customer","period":{"from","to"},
  "lines":[{"trip_folio","trip_date","total","paid","balance"}],
  "total_balance":0.0,"currency","pdf_path":null }

## CartaPorteDraft → CartaPorteStamp (key: cartaporte)
IN: { "empresa_id","trip_folio","cfdi_type":"traslado|ingreso",
  "mercancias":[{"descripcion","cantidad","peso_kg","clave_prod_serv"}],
  "extra": {...campos CCP no derivables del trip} }
El skill deriva del trip/unit/driver: origen, destino, vehículo,
placas, operador, licencia. OUT:
{ "stamp_folio":"CP-0010","stamp_status":"draft|stamped|error",
  "uuid_sat":null,"xml_path":null,"pdf_path":null,
  "pac_provider","error_detail":null }

## SettlementInput → Settlement (key: settlement)
IN: { "empresa_id","driver_key","period":{"from","to"} }
El skill junta trips cerrados del driver en el periodo + advances
no liquidados. Cálculo por pay_scheme del driver:
per_trip: pay_rate * num_trips | percent: pay_rate% * sum(trip_profit)
| salary: pay_rate fijo.
OUT: { "settlement_folio":"S-0007","trips_included":[...],
  "gross_amount","advances_deducted","other_deductions",
  "net_amount","currency","status":"draft","receipt_pdf_path":null }
net = gross - advances - other. SIEMPRE Python.

## AdvanceInput → Advance (key: advance)
{ "empresa_id","driver_key","amount","advance_date","concept",
  "trip_folio":null } → + { "advance_folio":"A-0012","settled_in":null }

## FuelLoadInput → FuelLoad (key: fuel_load)
{ "empresa_id","unit_key","driver_key":null,"trip_folio":null,
  "load_date","liters","amount","odometer_km","station":null,
  "doc_id":null } → + { "fuel_folio":"F-0033",
  "price_per_liter": amount/liters (Python) }
Foto de ticket: mismo patrón vision que Expense.

## EfficiencyReport (key: efficiency) — SIEMPRE calculado
{ "empresa_id","unit_key","period":{...},
  "km_traveled","liters_loaded","km_per_liter",
  "expected_km_per_liter","deviation_pct",
  "flag":"ok|warning|alert" }
warning si deviation_pct<-10; alert si <-20 (umbral en
context.get("alert_threshold_pct")).

## MaintenancePlan / Service / PartMovement
(keys: maintenance_plan, service, part_movement)
Plan: { "empresa_id","unit_key","service_type","every_km",
  "every_days","last_service_km","last_service_date" }
→ next_due_* calculado en Python.
Service: registra servicio real, actualiza plan y odómetro de unit.
PartMovement: in|out sobre parts, stock nunca negativo
(out>stock → {"ok":false,"error":"insufficient_stock"}).

## RateInput / QuoteInput → Quote (key: quote)
Rate: { "empresa_id","rate_key","origin","destination","cargo_type",
  "base_price","price_per_km","price_per_ton","currency" }
Quote IN: { "empresa_id","customer","origin","destination",
  "cargo_type","weight_tons","distance_km":null }
Cálculo: buscar rate matching (origin+destination+cargo_type) →
quoted_price = base + km*price_per_km + tons*price_per_ton.
Sin rate matching → {"ok":false,"error":"no_rate_found"} +
sugerencia de rates cercanas en warnings.
OUT: + { "quote_folio":"Q-0019","valid_until","status":"draft",
  "pdf_path":null }

## LoadInput → Load (key: load) — FASE 2
{ "publisher_empresa_id","origin","destination","cargo_type",
  "weight_tons","pickup_date","offered_price","currency",
  "requirements":null } → + { "load_folio":"L-0100","status":"open" }
Match: load_match devuelve candidatos (empresas con unidades
compatibles y trips que terminan cerca del origin) — nunca
auto-acepta; load_accept requiere confirmación de ambas partes.

## REGLA UNIVERSAL
- Output SIEMPRE {"ok":true,"data":{KEY: CONTRATO,"warnings":[...]}}
  o {"ok":false,"error":"snake_case_error"}
- empresa_id presente en todo input.
- Montos derivados (profit, balance, net, price_per_liter,
  km_per_liter, quoted_price) SIEMPRE en Python.
- IA solo para: extracción de tickets (vision), redacción de
  recordatorios de cobro. Nunca para cálculos ni IDs.
