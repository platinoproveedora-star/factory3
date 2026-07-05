=== BRIEF MÓDULO 4 — SETTLEMENTS4ALL (vertical_fleet4all_settlements) ===
[Pegar 00_REGLAS_GLOBALES_FLEET4ALL.md arriba]
Contratos: SettlementInput/Settlement, AdvanceInput/Advance.

SKILLS (4):
1. advance_capture — registra anticipo a driver (A-NNNN).
   settled_in=null hasta que un settlement lo consuma.
2. settlement_calculate — junta trips CLOSED del driver en el
   periodo no incluidos en otro settlement + advances con
   settled_in=null. Cálculo por drivers.pay_scheme:
   per_trip: pay_rate*len(trips) | percent: pay_rate/100*sum(profit)
   | salary: pay_rate. net = gross - advances - other_deductions
   (other de context, default 0). TODO en Python. Status=draft.
   Con context["approve"]=true → status=approved y marca advances
   settled_in=S-folio (transaccionalidad: si falla el update de
   advances, no aprobar — reportar db_persistence_failed).
3. receipt_generate — recibo de liquidación en PDF
   (/tmp/fleet4all_receipts/): desglose de trips, comisión,
   anticipos, neto. Bilingüe. dry_run: contenido en memoria,
   pdf_path=null.
4. settlement_history — read-only: liquidaciones por driver,
   totales por periodo, anticipos pendientes de descontar.

ERRORES: driver_not_found | no_trips_in_period |
already_settled | db_persistence_failed | file_write_failed
TERMINADO: flujo advance→calculate→approve→receipt corre con
EMP_DEMO_FLEET; correr calculate 2 veces no duplica settlements.
