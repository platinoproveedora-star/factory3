=== BRIEF MÓDULO 3 — CARTAPORTE4ALL (vertical_fleet4all_cartaporte) ===
[Pegar 00_REGLAS_GLOBALES_FLEET4ALL.md arriba]
Contratos: CartaPorteDraft/CartaPorteStamp.
PRERREQUISITO: cuenta sandbox con PAC (SW Sapien o Facturama) —
credenciales via os.environ (PAC_USER, PAC_PASSWORD, PAC_URL),
NUNCA hardcodeadas. Desarrollo 100% contra sandbox.
Referencia PERMITIDA: patrón envelope encryption de Conta4all
(KEK env var, DEK por secreto, AES-256-GCM, kek_version).

SKILLS (5):
1. csd_vault — guarda/recupera CSD (cer, key, password) del tenant
   en fleet4all.fiscal_credentials con envelope encryption.
   NUNCA loggear ni devolver material criptográfico en claro en
   data; solo status y valid_until. internal_only: true en manifest.
2. cartaporte_build — arma el JSON/XML del CFDI + complemento
   Carta Porte 3.1 derivando del trip (origen/destino), unit
   (placas, año, tipo), driver (nombre, licencia) + mercancias del
   input. Campos faltantes → {"ok":false,"error":"missing_fields",
   "data":{"missing":[...]}} para que el bot los pida uno a uno.
   Genera draft en fleet4all.cartaporte_stamps (CP-NNNN).
3. cartaporte_validate — validación local ANTES de gastar timbre:
   estructura, catálogos SAT básicos (claves de unidad, prod/serv
   de autotransporte), RFC formato, peso>0. Reglas en dict,
   extensibles. NO llama al PAC.
4. pac_stamp — envía el draft al PAC (sandbox default). Guarda
   uuid_sat, xml_path (/tmp/fleet4all_cfdi/), status=stamped.
   Error del PAC → status=error + error_detail legible.
   dry_run=True: valida contra el PAC sin timbrar si el API lo
   permite; si no, solo cartaporte_validate local + warning.
   Idempotencia: draft ya stamped → devuelve el stamp existente,
   NUNCA re-timbra.
5. cartaporte_cancel — cancelación ante el PAC con motivo SAT
   (catálogo 01-04). Requiere context["confirm"]=true explícito.

ERRORES: missing_fields | invalid_cartaporte | pac_error |
credentials_not_found | already_stamped | db_persistence_failed
TERMINADO: build→validate→stamp corre en sandbox con trip de
EMP_DEMO_FLEET y devuelve uuid_sat de prueba.
