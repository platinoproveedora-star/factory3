=== BRIEF MÓDULO 7 — QUOTES4ALL (vertical_fleet4all_quoting) ===
[Pegar 00_REGLAS_GLOBALES_FLEET4ALL.md arriba]
Contratos: RateInput/Rate, QuoteInput/Quote.
Referencia PERMITIDA (lectura): EMP_COTI4ALL / Cotizaciones4all
para reutilizar patrón de PDF y folios si aplica.

SKILLS (3):
1. rate_manage — CRUD de tarifario por empresa: rutas
   (origin+destination), cargo_type, componentes base/km/ton.
   Normalizar origin/destination a lowercase sin acentos (Python)
   para matching consistente.
2. quote_build — busca rate por (origin, destination, cargo_type);
   fallback: solo (origin, destination). quoted_price = base +
   distance_km*price_per_km + weight_tons*price_per_ton
   (componentes null = 0). Sin match →
   {"ok":false,"error":"no_rate_found"} + rates de la misma origin
   en warnings. valid_until = hoy + context.get("valid_days", 7).
   Folio Q-NNNN, status=draft. context["mark_sent"]=true → sent.
   Skill extra de conversión: quote aceptada →
   context["accept"]=true crea trip via SkillRunner (trip_from
   quote: customer, origin, destination, sale_price=quoted_price)
   y liga quotes.trip_folio.
3. quote_pdf_send — PDF de cotización (/tmp/fleet4all_quotes/):
   datos de la empresa emisora (de context["company_profile"]),
   ruta, precio, vigencia, condiciones. Bilingüe. dry_run:
   memoria + pdf_path=null. Envío por canal solo con
   dry_run=false y send_channel configurado.

ERRORES: no_rate_found | rate_exists | quote_not_found |
db_persistence_failed | file_write_failed
TERMINADO: rate→quote→pdf→accept(crea trip) corre con
EMP_DEMO_FLEET end-to-end.
