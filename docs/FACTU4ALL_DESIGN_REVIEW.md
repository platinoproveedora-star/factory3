# Factu4All / vertical_factu4all - Diseño MVP

## Objetivo

Crear una vertical genérica de facturación para México que pueda ser usada por cualquier módulo Apps4All.

Producto:

- Nombre comercial: Factu4All
- Skill vertical: vertical_factu4all
- Schema Supabase: factu4all
- Module code: factu4all
- País inicial: México
- PAC inicial: Facturama Multiemisor Sandbox

Flujo objetivo:

Remisión, pedido, venta directa u otro documento facturable -> Factu4All -> CFDI 4.0 timbrado -> UUID -> XML/PDF.

La primera implementación debe empezar por factura directa desde Factu4All, no desde remisiones.

## Principio de arquitectura

Factu4All debe ser independiente de los módulos origen.

Los módulos origen no deben llamar Facturama ni conocer detalles del PAC. Solo deben mandar un documento facturable normalizado.

Factu4All debe resolver:

- Empresa
- Usuario/permisos Apps4All
- Emisor fiscal
- Cliente/proveedor fiscal
- Productos fiscales
- Series y folios
- PAC
- CFDI
- XML/PDF
- Kardex fiscal

## Multiempresa

Factu4All debe soportar múltiples empresas.

Cada empresa puede tener:

- Su propio RFC emisor
- Su propio PAC
- Sus propias credenciales de PAC
- Sus propios CSD
- Varias series y folios
- Clientes/proveedores fiscales propios
- Catálogo fiscal propio
- Productos ligados a su sistema origen

Todo debe separarse por company_id.

## PAC

PAC inicial:

- Facturama
- Modo: Multiemisor
- Ambiente inicial: Sandbox

Razón:

Facturama API Web está más orientada a un solo emisor y catálogos dentro de Facturama. Factu4All necesita multiempresa/multi-RFC y su propia base fiscal, por eso conviene Multiemisor.

Endpoints relevantes de Facturama:

- Crear CFDI 4.0 Multiemisor: POST /api-lite/4/cfdis
- Consultar CFDI: GET /api-lite/cfdis/{id}
- Descargar XML/PDF/HTML: GET /api/Cfdi/{format}/{type}/{id}
- Para Multiemisor, type = issuedLite
- Cancelar CFDI: DELETE /api-lite/cfdis/{id}?motive={motive}&uuidReplacement={uuidReplacement}

Autenticación:

- Basic Auth con usuario/password Facturama
- No guardar credenciales planas en base de datos
- Guardar referencias a secretos o env vars

## PACAdapter

El ERP no debe acoplarse a Facturama.

`vertical_factu4all/pac_stamp` tiene su propio `PacAdapter` — copia independiente, no depende de `vertical_fleet4all_cartaporte` (son dos productos distintos; Factu4All no debe colgar de la carpeta de Fleet4All). Mismo patrón/contrato que cartaporte (stamp/cancel, `NullPacAdapter` sandbox simulado, idempotencia por status), pero código propio.

Contrato `PacAdapter`:

- stamp
- cancel
- get_cfdi
- download_xml
- download_pdf

Primera implementación: `FacturamaPacAdapter` (placeholder, `NotImplementedError` hasta tener credenciales Multiemisor Sandbox reales) + `NullPacAdapter` (sandbox simulado, ya funcional para probar el flujo completo sin timbre real).

`vertical_factu4all/pac_stamp`: recibe el draft de factura, llama `get_pac_adapter()`, persiste en `cfdi_documents` (schema factu4all). Evita doble timbrado: si el CFDI del `source_id` ya está `stamped`, devuelve el existente sin re-timbrar.

Duplicación aceptada conscientemente vs. `vertical_fleet4all_cartaporte/pac_stamp` — mismo patrón, dos implementaciones independientes, cero acoplamiento entre productos.

## Schema y tablas propuestas

Schema:

- factu4all

Tablas base:

- factu4all_company_settings
- pac_accounts
- issuer_profiles
- folio_series
- parties
- products
- cfdi_documents
- cfdi_item_movements
- document_files
- source_catalogs
- product_source_links
- party_source_links
- supplier_product_mappings

## factu4all_company_settings

No activa el módulo — eso ya lo resuelve `platform.access_grants` vía `apps4all_marketplace_module_activate` (marketplace). Esta tabla solo guarda configuración propia de Factu4All por empresa una vez que el módulo ya está activo.

Campos mínimos:

- id
- folio
- company_id
- country = MX
- default_pac_provider
- default_environment
- created_at
- updated_at
- metadata

Antes de timbrar, Factu4All valida que exista `access_grants` activo para `company_id` + `module_code=factu4all` en `platform` (no duplica ese chequeo, lo consulta).

## pac_accounts

Configuración del PAC por empresa.

Campos mínimos:

- id
- folio
- company_id
- pac_provider
- environment
- credential_ref
- status
- created_at
- updated_at
- metadata

No guardar usuario/password plano. Solo referencias a secretos.

## issuer_profiles

Datos fiscales del emisor.

Campos mínimos:

- id
- folio
- company_id
- rfc
- legal_name
- fiscal_regime
- expedition_place
- commercial_name
- fiscal_email
- fiscal_address
- pac_provider
- pac_account_id
- csd_status
- environment
- status
- created_at
- updated_at
- metadata

Datos críticos para Facturama:

- Issuer.Rfc
- Issuer.Name
- Issuer.FiscalRegime
- ExpeditionPlace

## folio_series

Series y folios por empresa.

Cada empresa puede tener varias series.

Campos mínimos:

- id
- folio
- company_id
- cfdi_type
- series
- current_number
- next_number
- environment
- pac_provider
- is_default
- status
- created_at
- updated_at
- metadata

Ejemplo:

- F / ingreso / sandbox / Facturama / default
- A / ingreso / production
- B / credito / production

## parties

Base fiscal independiente de clientes y proveedores.

No depender directamente del cliente operativo. Se guarda referencia al origen y snapshot fiscal propio.

Campos mínimos:

- id
- folio
- company_id
- source_system
- source_schema
- source_table
- source_id
- source_folio
- party_type
- source_display_name
- rfc
- legal_name
- tax_regime
- tax_zip_code
- cfdi_use_default
- billing_email
- billing_address
- status
- created_at
- updated_at
- metadata

Regla:

- ERP = verdad operativa
- Factu4All = verdad fiscal

## products

Catálogo fiscal propio de Factu4All.

Debe conservar el producto real separado aunque comparta la misma clave SAT con otros productos.

Ejemplo:

- Varilla 3/8 -> SAT 30102404
- Varilla 1/2 -> SAT 30102404
- Varilla 5/8 -> SAT 30102404

Esto permite reportar por producto real y por clave SAT.

Campos mínimos:

- id
- folio
- company_id
- source_system
- source_schema
- source_table
- source_id
- source_folio
- source_product_key
- source_product_name
- fiscal_product_name
- fiscal_description
- sat_product_key
- sat_unit_key
- sat_unit_name
- tax_object
- iva_rate
- ieps_rate
- category
- sat_group_key
- status
- created_at
- updated_at
- metadata

Doble clave obligatoria:

- source_product_key: clave/SKU del sistema origen
- sat_product_key: clave SAT

## cfdi_documents

Registro universal de CFDIs emitidos y recibidos.

Campos mínimos:

- id
- folio
- company_id
- direction
- cfdi_type
- business_effect
- source_system
- source_schema
- source_table
- source_type
- source_id
- source_folio
- party_id
- party_type
- party_rfc_snapshot
- party_legal_name_snapshot
- payment_method
- payment_form
- currency
- pac_provider
- pac_account_id
- environment
- series
- cfdi_folio
- uuid
- status
- subtotal
- discount_total
- tax_total
- total
- xml_storage_path
- pdf_storage_path
- pac_request
- pac_response
- pac_error
- issued_at
- cancelled_at
- created_at
- updated_at
- metadata

Estados:

- draft
- previewed
- stamping
- stamped
- stamp_error
- received
- cancelled
- cancel_error

Prevención de doble timbrado:

Debe impedirse más de un CFDI activo/timbrado para:

- company_id
- source_system
- source_type
- source_id

## cfdi_item_movements

Kardex fiscal.

No controla inventario físico; controla movimientos fiscales por CFDI.

Debe permitir consultar:

- Qué se facturó por producto real
- Qué se facturó por clave SAT
- Qué se recibió por proveedor
- Qué se emitió a clientes
- Entradas fiscales por XML recibido
- Salidas fiscales por CFDI emitido

Campos mínimos:

- id
- folio
- company_id
- cfdi_document_id
- uuid
- movement_direction
- document_direction
- business_effect
- source_document_id
- source_document_folio
- party_id
- party_type
- product_id
- source_product_id
- source_product_key
- source_product_name
- fiscal_product_name_snapshot
- sat_product_key_snapshot
- sat_unit_key_snapshot
- sat_group_key_snapshot
- quantity
- unit_price
- subtotal
- discount_amount
- tax_amount
- total
- issued_at
- cancelled_at
- created_at
- metadata

Movimientos:

- out: factura emitida
- in: factura recibida
- out_cancelled: cancelación emitida
- in_cancelled: cancelación recibida

## document_files

Archivos XML/PDF/acuse.

Usar bucket privado:

- factu4all-documents

Path recomendado:

- {company_id}/{environment}/{cfdi_type}/{yyyy}/{mm}/{uuid}.xml
- {company_id}/{environment}/{cfdi_type}/{yyyy}/{mm}/{uuid}.pdf
- {company_id}/{environment}/{cfdi_type}/{yyyy}/{mm}/{uuid}_acuse.xml
- {company_id}/{environment}/{cfdi_type}/{yyyy}/{mm}/{uuid}_acuse.pdf

Campos mínimos:

- id
- folio
- company_id
- cfdi_document_id
- uuid
- file_type
- storage_bucket
- storage_path
- content_type
- size_bytes
- checksum
- created_at
- metadata

## Facturas recibidas

Factu4All debe tener pantalla para subir XML de proveedores.

Flujo:

- Usuario sube XML
- Factu4All parsea CFDI
- Emisor del XML se guarda como proveedor fiscal
- Receptor debe coincidir con la empresa configurada
- Conceptos se guardan como movimientos del kardex fiscal
- XML original se guarda en storage
- Productos quedan mapeados o pendientes de mapear

Importante:

Un CFDI recibido de proveedor normalmente es tipo I emitido por el proveedor. Para nosotros no llamarlo "CFDI tipo egreso" si eso confunde con tipo E del SAT. Internamente usar:

- direction = received
- business_effect = purchase_expense

## supplier_product_mappings

Mapeo de productos detectados en XML proveedor contra productos fiscales Factu4All.

Campos mínimos:

- id
- folio
- company_id
- supplier_party_id
- supplier_rfc
- supplier_product_key
- supplier_product_description
- sat_product_key
- sat_unit_key
- factu4all_product_id
- confidence
- status
- created_at
- updated_at
- metadata

Matching sugerido:

- supplier_rfc + NoIdentificacion
- sat_product_key + description
- mapeo manual previo
- si no encuentra, queda unmapped

## Source catalogs

Factu4All debe poder usar catálogos origen por empresa, como Coti4All.

Ejemplo Duralon:

- Productos: uc101_proy004.erp_products
- Clientes/proveedores: uc101_proy004.erp_parties
- Remisiones: uc101_proy002.sales_documents

Pantalla debe permitir elegir base de productos a la que el usuario tenga acceso.

Internamente, antes de timbrar, todo producto seleccionado debe existir o crearse en factu4all.products.

## Pantallas MVP

Pestañas iniciales:

- Nueva factura
- Facturas emitidas
- Facturas recibidas
- Clientes fiscales
- Proveedores fiscales
- Productos fiscales
- Kardex fiscal
- Empresa / Configuración

## Nueva factura

Debe permitir:

- Seleccionar empresa
- Seleccionar serie
- Seleccionar cliente fiscal existente
- Crear cliente fiscal nuevo
- Seleccionar base/catálogo de productos
- Seleccionar producto fiscal existente
- Importar producto desde ERP
- Crear producto fiscal nuevo
- Agregar conceptos manuales
- Preview CFDI
- Timbrar Sandbox
- Descargar XML/PDF

## Empresa / Configuración

Debe capturar para Duralon:

- company_id
- RFC emisor
- Razón social fiscal
- Régimen fiscal
- Código postal de expedición
- Nombre comercial
- Correo fiscal
- Dirección fiscal
- PAC
- Ambiente
- Estado de credenciales
- Estado de CSD
- Series/folios
- Catálogos origen

Validación de preparación:

- Emisor fiscal completo
- PAC Sandbox configurado
- CSD Sandbox cargado
- Serie default activa
- Productos listos
- Clientes fiscales disponibles
- Listo para timbrar Sandbox

## Primer caso real

El primer caso real será factura directa desde Factu4All.

No empezar todavía con remisión.

Flujo:

- Entrar a Factu4All
- Empresa Duralon activa
- Capturar o seleccionar cliente fiscal
- Seleccionar productos importados desde PROY-004
- Confirmar claves SAT/unidades/impuestos
- Elegir serie
- Preview CFDI
- Timbrar con Facturama Sandbox
- Guardar UUID
- Guardar XML/PDF
- Insertar movimientos en kardex fiscal

## Producto actual Duralon

Catálogo real activo encontrado en PROY-004:

| Producto ERP | Folio | Unidad ERP | Clave SAT | Unidad SAT | Unidad fiscal | IVA | Estado |
|---|---|---|---|---|---|---|---|
| Alambre recocido kg | PROD-00019 | kg | 30264401 | KGM | Kilogramo | 16% | revisar |
| ALAMBRON | PROD-00006 | KG | 30264401 | KGM | Kilogramo | 16% | revisar |
| Armex Castillo 15x15-4 electros | PROD-00020 | pieza | 30111903 | H87 | Pieza | 16% | ready |
| Armex Castillo 15x20-4 electros | PROD-00021 | pieza | 30111903 | H87 | Pieza | 16% | ready |
| Calidra hidróxido de calcio 22.50kg | PROD-00004 | Bulto | 12352319 | H87 | Bulto | 16% | ready |
| CEMENTO GRIS 50 KG | PROD-00007 | BULTOS | 30111601 | H87 | Bulto | 16% | ready |
| Cemento gris CPC30 RS 50kg | PROD-00002 | Bulto | 30111601 | H87 | Bulto | 16% | ready |
| Malla electrosoldada 6-6/4-4 rollo | PROD-00018 | ROLLO | 30111903 | XRO | Rollo | 16% | ready |
| MALLA ELECTROSOLDADA 66/1010 | PROD-00016 | pieza | 30111903 | H87 | Pieza | 16% | ready |
| VARILLA CORRUGADA 1/2" | PROD-00003 | pieza | 30102404 | H87 | Pieza | 16% | ready |
| VARILLA CORRUGADA 3/8 | PROD-00015 | pieza | 30102404 | H87 | Pieza | 16% | ready |
| Varilla corrugada 3/8 aceros | PROD-00005 | pieza | 30102404 | H87 | Pieza | 16% | ready |

Notas:

- Varillas comparten clave SAT 30102404.
- Cementos comparten clave SAT 30111601.
- Mallas/Armex usan 30111903.
- Malla por rollo usa unidad SAT XRO.
- Cemento se factura como Bulto con UnitCode H87.
- Alambre/Alambrón deben validarse con XMLs de proveedor antes de marcarlos ready definitivo.

## Contrato universal de entrada

Factu4All debe aceptar dos modos:

- direct_invoice
- source_invoice

Para direct_invoice:

- company_id
- issuer_profile_id
- series_id
- customer/party fiscal
- items
- payment

Para source_invoice:

- company_id
- source_system
- source_schema
- source_table
- source_type
- source_id
- source_folio
- party_source_id
- party_type
- items
- payment

Factu4All completa datos fiscales desde su propia base.

## Reglas de timbrado

No timbrar si falta:

- RFC emisor
- Razón social emisor
- Régimen fiscal emisor
- Código postal de expedición
- PAC configurado
- CSD cargado
- Serie activa
- Cliente fiscal completo
- Producto fiscal ready
- Forma de pago
- Método de pago
- Uso CFDI
- Objeto de impuesto

Siempre preview antes de timbrar.

Evitar doble timbrado desde backend y base de datos.

## Fases sugeridas

Fase 1:

- Módulo Factu4All Apps4All
- Empresa Duralon configurada (primer tenant, activado vía marketplace)
- Login Apps4All completo (usuarios/roles, no dashboard_key)
- Schema factu4all
- Catálogo fiscal importado desde PROY-004
- Captura cliente fiscal nuevo
- Pantalla configuración empresa
- Factura directa
- Preview
- Facturama Sandbox
- Guardar UUID/XML/PDF

Fase 2:

- Facturas recibidas
- Upload XML
- Parse CFDI
- Proveedores fiscales automáticos
- Kardex fiscal entrada
- Mapeo proveedor/producto

Fase 3:

- Facturar remisiones PROY-002
- Botón FACTURAR en remisión
- Preview desde remisión
- Timbrado
- Evitar doble timbrado
- Descarga XML/PDF

Fase 4:

- Cancelación CFDI
- Acuses
- Producción
- Más PACs
- Reportes fiscales avanzados

## Pendientes antes de codificar

Bloqueantes (sin esto no se puede empezar a construir el módulo):

- [x] `companies/EMP_FACTU4ALL/projects/PROY-001_FACTU4ALL/` creado (company_id=EMP_FACTU4ALL, module_code=factu4all, schema=factu4all, platform=vercel). Dashboard Next.js con auth Apps4All completo (login/logout/me/grants, middleware, lib/factory.ts, lib/platform.ts) ya clonado y pasando `apps4all_dash_health_check` con 0 blockers/0 warnings. De paso se dejó reusable: `vertical_apps4all_dash/templates/base_dashboard` ahora es un template real (ya no un placeholder) y `vertical_apps4all_factory/apps4all_company_project_scaffold` orquesta company+dashboard en un solo skill para cualquier módulo Apps4All futuro.
- [x] `vertical_factu4all/pac_stamp` creado con su propio `PacAdapter` (copia independiente, sin depender de fleet4all_cartaporte). Contrato completo (stamp/cancel/get_cfdi/download_xml/download_pdf). `NullPacAdapter` sandbox simulado ya funcional. `FacturamaPacAdapter` queda como placeholder (`NotImplementedError`) hasta tener credenciales Multiemisor Sandbox reales — lee `FACTU4ALL_PAC_PROVIDER/USER/PASSWORD/URL` o `context.pac_*` (vault). Idempotente por `company_id+folio`. Registrado en `registry.json`, 0 blockers en `factory_no_hardcode_audit`.
- **Pendiente real:** implementar `stamp`/`cancel`/`get_cfdi`/`download_xml`/`download_pdf` de `FacturamaPacAdapter` contra la API real cuando haya credenciales Sandbox — hoy son placeholders honestos, no simulados como estables.
- [x] `vertical_factu4all/factu4all_schema_setup` creado y **ejecutado en Supabase real** — 13 tablas creadas y schema `factu4all` expuesto en la Data API (`vertical_supabase/supabase_expose_schema`).
- [x] CRUD creados y probados en vivo: `issuer_profile_manage`, `party_manage`, `product_manage`, `folio_series_manage` (create/update/list, `next` reserva folio consecutivo).
- [x] `vertical_factu4all/cfdi_build` creado — resuelve issuer/party, reserva folio via `folio_series_manage`, calcula subtotal/IVA/total desde items, crea el draft en `cfdi_documents`.
- [x] **Flujo completo probado end-to-end contra Supabase real** (emisor -> cliente -> producto -> serie -> `cfdi_build` -> `pac_stamp` sandbox simulado -> reintento bloqueado por idempotencia). Datos de prueba limpiados después.

No bloqueantes — se capturan desde la pantalla "Empresa / Configuración" una vez exista el primer dashboard, no antes de codificar:

- Credenciales Facturama Sandbox (usuario/password vía vault, no env var fija — ver `pac_accounts.credential_ref`).
- Datos fiscales de Duralon emisor (RFC, régimen fiscal, CP de expedición, razón social) — ya los tiene el usuario, se capturan en `issuer_profiles` vía la pantalla, no como seed previo.
- CSD Sandbox (se sube desde la misma pantalla, vía `csd_vault`).
- Validar claves SAT de Alambre recocido y Alambrón con XMLs de proveedor — no bloquea Fase 1 (van como `status=revisar` en `products`, se resuelven antes de facturarlos, no antes de codificar).

## Dashboard — listo, solo falta configurar

Construido completo sobre `companies/EMP_FACTU4ALL/projects/PROY-001_FACTU4ALL/` (clonado del shell real de Coti4All, con auth Apps4All propio):

- **Vault propio** `vertical_factu4all/secrets_vault_manage` (schema `factu4all.secrets_vault`, cifrado DEK/AES-256-GCM + KEK maestra `PLATFORM_KEK_V1`) — reemplaza el plan original de reusar `security_secret_store` porque esa tabla tiene FK a un usuario puntual (`platform.users`), no sirve para secretos a nivel empresa. Guarda credenciales PAC y CSD. Probado en vivo (store/retrieve/status/rotación).
- `pac_stamp` ahora resuelve credenciales automáticamente desde el vault (`scope_type=pac_credentials`) cuando no vienen en `context` — probado en vivo: con credenciales guardadas selecciona `FacturamaPacAdapter` real en vez del sandbox simulado.
- **Páginas construidas:** `/dashboard` (resumen + checklist de que falta), `/settings` (emisor fiscal, credenciales PAC, CSD, series de folios — todo editable), `/invoices/new` (armar factura: cliente existente o nuevo, conceptos, preview de totales, crear borrador, timbrar), `/invoices` (lista con botón Timbrar para borradores).
- **API routes** (`app/api/factu4all/*`) todas con `getSession()` + `requireCompanyModuleGrant(..., "factu4all")` antes de tocar cualquier skill.
- `npm run build` — compila limpio, 0 errores TypeScript, 9 páginas + 11 rutas API. `factory_no_hardcode_audit` en 0 blockers. `apps4all_dash_health_check` en 0 blockers/0 warnings.

**Lo único que falta ahora es configurar desde la pantalla `/settings` una vez desplegado:** RFC/datos fiscales del emisor, usuario/password/URL de Facturama Sandbox, y el CSD. Todo lo demás (schema, skills, CRUD, timbrado, vault, UI) ya está construido y probado.

