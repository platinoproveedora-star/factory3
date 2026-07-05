=== BRIEF MÓDULO 2 — COLLECT4ALL (vertical_fleet4all_collections) ===
[Pegar 00_REGLAS_GLOBALES_FLEET4ALL.md arriba]
Contratos: PaymentInput/Payment, Receivable, Statement.
Referencia PERMITIDA (lectura): lógica _sync_cxc / _build_cxc_view
en EMP_LOGPLAT/dashboard/app.py.

SKILLS (4):
1. payment_capture — registra payment (folio P-NNNN); valida trip
   exista; al persistir llama internamente receivables_sync del
   trip (patrón skill-llama-skill del repo con SkillRunner).
2. receivables_sync — IDEMPOTENTE. Por trip: total=sale_price,
   paid=sum(payments), balance=total-paid, status por reglas del
   contrato. Crea receivable si no existe (folio R-NNNN = mismo
   número del trip). Actualiza trips.payment_status espejo.
   Input: empresa_id + trip_folio, o empresa_id + all=true
   (reconstrucción completa, clon de _reparar_cxc).
3. statement_generate — estado de cuenta por customer y periodo.
   Con context["pdf"]=true genera PDF simple (reportlab si está,
   si no HTML→archivo) a /tmp/fleet4all_statements/. dry_run=True:
   contenido en memoria, pdf_path=null.
4. collection_reminder — genera mensajes de cobro para receivables
   con balance>0 según etapa: due-3d (recordatorio amable), due
   (vencimiento hoy), +7d (overdue firme). Redacción con Haiku
   usando tono profesional, bilingüe. dry_run default True devuelve
   los mensajes SIN enviar; envío real solo con dry_run=false y
   context["send_channel"] configurado. NUNCA amenaza ni lenguaje
   agresivo; solo datos del adeudo y datos de contacto.

ERRORES: trip_not_found | customer_not_found | no_receivables |
db_persistence_failed | file_write_failed
TERMINADO: pipeline payment→sync→statement corre con EMP_DEMO_FLEET;
sync idempotente (correrlo 2 veces = mismo estado).
