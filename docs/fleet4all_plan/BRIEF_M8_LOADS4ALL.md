=== BRIEF MÓDULO 8 — LOADS4ALL (vertical_fleet4all_loadboard) ===
[Pegar 00_REGLAS_GLOBALES_FLEET4ALL.md arriba]
FASE 2 — NO ARRANCAR hasta que M1-M3 tengan usuarios reales.
Este brief queda listo para esa fecha.
Contratos: LoadInput/Load.
NOTA: tabla fleet4all.loads es CROSS-TENANT por diseño
(publisher_empresa_id + matched_empresa_id) — única del vertical.
Extremar validación de permisos: una empresa solo edita sus loads.

SKILLS (4):
1. load_publish — publica carga (L-NNNN global, no por empresa —
   es tablero compartido). Valida publisher_empresa_id, origin,
   destination, pickup_date futura. status=open.
2. load_match — read-only para transportistas: loads open
   filtradas por origin cercana al destino de sus trips activos
   (matching por texto normalizado v1; geo real = v2), por
   unit_type disponible y pickup_date compatible. NUNCA expone
   datos de contacto hasta accept mutuo — solo folio, ruta,
   carga, precio.
3. load_accept — dos pasos: transportista manda interés
   (status queda open + registro de interés), publisher confirma
   (context["publisher_confirm"]=true) → status=matched +
   matched_empresa_id. Solo entonces se intercambian contactos
   en la respuesta. Race: primer confirm gana; segundo recibe
   {"ok":false,"error":"already_matched"}.
4. trip_from_load — al matched, el transportista crea su trip
   via SkillRunner (customer=publisher, origin/destination/
   sale_price=offered_price) y liga matched_trip_folio;
   status=in_transit. Al trip_close → status=done.

ERRORES: load_not_found | already_matched | not_load_owner |
invalid_dates | db_persistence_failed
TERMINADO: publish(empresa A)→match(empresa B)→accept ambos→
trip_from_load corre con dos empresas demo.
