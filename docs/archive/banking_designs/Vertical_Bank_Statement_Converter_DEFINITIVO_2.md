# Vertical Bank Statement Converter — DEFINITIVO para diseñar/codificar

Documento único. Sustituye versiones previas del diseño del converter. Este documento define la arquitectura cerrada de `vertical_bank_statement_converter` para Factory 3. No codifica implementación; fija el contrato funcional, de datos, aislamiento, almacenamiento, perfiles, validación y relación con los demás verticales.

---

## 0. Objetivo

`vertical_bank_statement_converter` convierte PDFs de estados de cuenta bancarios con texto nativo en movimientos normalizados, auditables y reutilizables por `vertical_erp_reconciliation` o cualquier otro consumidor.

Este vertical es una capa pura de extracción, normalización, validación y exportación.

No conoce ni escribe en:

- `banks_movements`
- saldos bancarios
- autorizaciones
- pólizas contables
- conciliaciones finales

Su salida principal son líneas limpias en `statement_extracted_lines`, con trazabilidad suficiente para auditar contra el PDF original.

---

## 1. Alcance v1

### 1.1 Formato soportado

v1 soporta únicamente:

- PDF con texto nativo extraíble

Aunque el modelo deja abierta compatibilidad futura con CSV/TXT, el skill `bank_statement_extract` en v1 solo debe aceptar `source_format='pdf'`.

### 1.2 Bancos soportados en v1

Perfiles iniciales:

- Banorte — `banorte_enlace_global` — layout `Enlace Global PM`
- BBVA — `bbva_maestra_pyme` — layout `Maestra PYME`

### 1.3 Fuera de alcance v1

Quedan fuera de v1:

- OCR
- PDFs escaneados
- BanBajío
- Santander
- HSBC
- Scotiabank
- CSV
- TXT
- escritura directa en `vertical_erp_banks`
- lógica de conciliación
- lógica de autorización

BanBajío y Santander quedan para fase 2 porque las pruebas iniciales indicaron PDFs sin capa de texto utilizable.

---

## 2. Patrón de aislamiento

Este vertical debe seguir el mismo patrón de aislamiento físico que `vertical_erp_banks`.

Cada empresa vive en su propio schema de Supabase.

```text
EMP_DURALON  -> schema propio
EMP_PLATINO  -> schema propio
Otra empresa -> schema propio
```

El aislamiento real es físico por schema. No se usa una tabla compartida con `WHERE empresa_id` como mecanismo principal.

`empresa_id` se guarda en cada fila como segunda capa de integridad y trazabilidad, pero no sustituye al aislamiento por schema.

---

## 3. Resolución de contexto

El contexto se resuelve igual que en los verticales ERP.

```text
erp_project_context_resolve
        ↓
resolve_statement_context
        ↓
schema
empresa_id
project_code
module_code = 'bank_statement_converter'
```

Debe existir un helper equivalente a:

```text
_statement_common.py
  resolve_statement_context(context)
```

Responsabilidades de `resolve_statement_context`:

1. Recibir `company_id` / `empresa_id`, `project_code` y opcionalmente `schema`.
2. Llamar o apoyarse en `vertical_erp/erp_project_context_resolve`.
3. Validar que el schema de empresa existe.
4. Devolver:

```json
{
  "empresa_id": "EMP_DURALON",
  "project_code": "PROY-00X_STATEMENTS",
  "schema": "emp_duralon_schema",
  "module_code": "bank_statement_converter"
}
```

Ningún skill debe escribir en un schema si el contexto no resolvió correctamente.

---

## 4. Arquitectura general

Flujo conceptual:

```text
PDF bancario
  ↓
Storage / input temporal
  ↓
Extracción de texto nativo
  ↓
Detección de perfil
  ↓
Construcción de bloques multi-línea
  ↓
Parser por perfil
  ↓
Normalización
  ↓
Validación contra resumen del banco
  ↓
statement_extractions
  ↓
statement_extracted_lines
  ↓
Excel / Reconciliation / revisión manual
```

El PDF original debe guardarse en Supabase Storage para auditoría, reprocesamiento y futuras mejoras de perfiles/OCR.

---

## 5. Storage del PDF original

### 5.1 Decisión

El PDF original sí se guarda.

No se guarda dentro de la base de datos. Se guarda en Supabase Storage.

La base de datos guarda solo:

- `storage_bucket`
- `storage_path`
- `file_hash`
- metadata del archivo

### 5.2 Bucket recomendado

Bucket:

```text
bank-statements
```

### 5.3 Path recomendado

```text
bank-statements/
  {empresa_id}/
    {bank_profile}/
      {yyyy}/
        {yyyy-mm-dd}_{file_hash_prefix}_{file_name}
```

Ejemplo:

```text
bank-statements/EMP_DURALON/banorte_enlace_global/2026/2026-06-20_a8f91c_estado_banorte_junio.pdf
```

### 5.4 Motivos

Guardar el PDF permite:

- auditoría futura
- reprocesamiento con perfiles nuevos
- validación manual
- entrenamiento de perfil nuevo
- soporte futuro de OCR
- evidencia ante diferencias de conciliación

---

## 6. Principio estructural universal

En Banorte y BBVA, un movimiento real no siempre es una línea única.

Cada movimiento se representa como bloque multi-línea:

- Una línea ancla
- Cero o más líneas de continuación

### 6.1 Línea ancla

Una línea ancla:

- inicia con fecha
- contiene monto
- puede contener saldo
- marca el inicio de un movimiento

### 6.2 Líneas de continuación

Las líneas de continuación:

- no inician un nuevo movimiento
- pueden contener RFC, banco emisor, concepto, referencia o clave de rastreo
- pertenecen al movimiento anterior

### 6.3 Regla de cierre del bloque

Un bloque termina cuando aparece la siguiente línea ancla.

La lógica de armado de bloques vive en el engine genérico, no dentro de cada perfil.

---

## 7. DDL — tablas

Todas las tablas viven dentro del schema de empresa `{schema}`.

### 7.1 `statement_extractions`

```sql
create table if not exists {schema}.statement_extractions (
  id uuid primary key default gen_random_uuid(),
  folio text unique not null,                 -- BSE-00001
  empresa_id text not null,
  project_code text not null,
  module_code text not null default 'bank_statement_converter',

  source_format text not null
    constraint statement_extractions_source_format_chk
    check (source_format in ('pdf','csv','txt')),

  bank_profile text not null,
  profile_version text not null default 'v1',
  bank_name text,

  account_number_mask text,
  statement_period_start date,
  statement_period_end date,

  file_name text,
  file_hash text not null,
  file_size_bytes bigint,
  mime_type text,

  storage_bucket text,
  storage_path text,

  total_lines_raw integer not null default 0,
  total_blocks_detected integer not null default 0,
  total_lines_extracted integer not null default 0,

  total_deposits_reported numeric(14,2),
  total_deposits_extracted numeric(14,2),
  validation_diff_deposits numeric(14,2),

  total_withdrawals_reported numeric(14,2),
  total_withdrawals_extracted numeric(14,2),
  validation_diff_withdrawals numeric(14,2),

  validation_status text not null default 'pendiente'
    constraint statement_extractions_validation_status_chk
    check (validation_status in ('pendiente','validado','con_diferencias','no_validable')),

  status text not null default 'extraido'
    constraint statement_extractions_status_chk
    check (status in ('extraido','con_errores','requires_ocr')),

  warnings jsonb not null default '[]',
  metadata jsonb not null default '{}',

  created_at timestamptz not null default now(),
  updated_at timestamptz
);
```

### 7.2 Índices de `statement_extractions`

```sql
create unique index if not exists statement_extractions_file_unique_idx
on {schema}.statement_extractions(bank_profile, file_hash);

create index if not exists statement_extractions_empresa_idx
on {schema}.statement_extractions(empresa_id, project_code);

create index if not exists statement_extractions_period_idx
on {schema}.statement_extractions(statement_period_start, statement_period_end);

create index if not exists statement_extractions_status_idx
on {schema}.statement_extractions(status, validation_status);
```

### 7.3 `statement_extracted_lines`

```sql
create table if not exists {schema}.statement_extracted_lines (
  id uuid primary key default gen_random_uuid(),
  folio text unique not null,                 -- BSL-00001
  empresa_id text not null,
  project_code text not null,
  module_code text not null default 'bank_statement_converter',

  extraction_id uuid not null references {schema}.statement_extractions(id),

  raw_line_order integer not null,

  transaction_date date,
  posting_date date,
  line_date date not null,

  description text,

  direction text not null
    constraint statement_extracted_lines_direction_chk
    check (direction in ('deposito','retiro')),

  amount numeric(14,2) not null,
  saldo numeric(14,2),

  clave_rastreo text,
  referencia text,

  confidence numeric(5,4) not null default 1.0000,
  parse_warnings jsonb not null default '[]',

  raw_text text not null,
  metadata jsonb not null default '{}',

  created_at timestamptz not null default now()
);
```

### 7.4 Índices de `statement_extracted_lines`

```sql
create index if not exists idx_bsl_extraction
on {schema}.statement_extracted_lines(extraction_id);

create index if not exists idx_bsl_rastreo
on {schema}.statement_extracted_lines(clave_rastreo);

create index if not exists idx_bsl_referencia
on {schema}.statement_extracted_lines(referencia);

create index if not exists idx_bsl_dates
on {schema}.statement_extracted_lines(line_date, posting_date, transaction_date);

create index if not exists idx_bsl_amount
on {schema}.statement_extracted_lines(amount);
```

---

## 8. Prefijos de folio

| Prefijo | Tabla | Uso |
|---|---|---|
| `BSE` | `statement_extractions` | extracción / archivo procesado |
| `BSL` | `statement_extracted_lines` | línea/movimiento extraído |

Los folios se generan con `reserve_erp_folio()` dentro del schema de empresa, siguiendo el patrón ERP existente.

---

## 9. Idempotencia

### 9.1 Regla

Antes de crear una extracción real:

1. Calcular `file_hash` SHA256 del binario del PDF.
2. Resolver/detectar `bank_profile`.
3. Buscar si ya existe:

```text
bank_profile + file_hash
```

Si existe, no se vuelve a insertar.

### 9.2 Output idempotente

```json
{
  "ok": true,
  "data": {
    "idempotent": true,
    "extraction": {},
    "lines_created": 0
  }
}
```

### 9.3 Storage e idempotencia

Si el PDF ya existe por `file_hash`, no debe duplicarse en Storage salvo que se decida explícitamente guardar otra copia por nombre. En v1, no se duplica.

---

## 10. Perfiles

Los perfiles viven en archivos JSON versionados.

```text
profiles/
  banorte_enlace_global.v1.profile.json
  bbva_maestra_pyme.v1.profile.json
```

Cada perfil debe contener:

- `bank_profile`
- `profile_version`
- `bank_name`
- markers de detección
- regex de línea ancla
- formato de fecha
- estrategia de monto
- estrategia de saldo
- regex de clave de rastreo
- regex de referencia
- regex de totales de resumen
- reglas de líneas a ignorar

El engine genérico no debe tener lógica hardcodeada de Banorte o BBVA, salvo el despacho por estrategia declarada en el perfil.

---

## 11. Perfil Banorte v1

Archivo:

```text
profiles/banorte_enlace_global.v1.profile.json
```

```json
{
  "bank_profile": "banorte_enlace_global",
  "profile_version": "v1",
  "bank_name": "Banorte",
  "detect_markers": ["ENLACE GLOBAL PM", "MONTO DEL DEPOSITO"],
  "anchor_regex": "^(\\d{2}-[A-Z]{3}-\\d{2})(.*)",
  "date_format": "%d-%b-%y",
  "date_locale_fix": {
    "ENE": "JAN",
    "ABR": "APR",
    "MAY": "MAY",
    "AGO": "AUG",
    "DIC": "DEC"
  },
  "amount_strategy": "single_column_two_amounts_right_aligned",
  "saldo_position": "last_money_value_in_anchor_line",
  "saldo_required_each_row": true,
  "rastreo_regex": "CVE\\s*RAST(?:REO)?\\s*[:\\s]+([A-Za-z0-9]+)",
  "referencia_regex": "REFERENCIA\\s*[:\\s]+([A-Za-z0-9]+)",
  "summary_deposits_regex": "Total\\s+de\\s+dep[oó]sitos\\s+\\$?\\s*([0-9,]+\\.\\d{2})",
  "summary_withdrawals_regex": "Total\\s+de\\s+retiros\\s+\\$?\\s*([0-9,]+\\.\\d{2})",
  "skip_line_patterns": ["^SALDO ANTERIOR", "^OTROS", "^Cargos Objetados"]
}
```

Reglas Banorte:

- Una sola fecha por movimiento.
- `transaction_date`, `posting_date` y `line_date` pueden usar la misma fecha.
- El saldo normalmente aparece en cada línea ancla.
- Si falta saldo en una línea donde el perfil lo espera, agregar warning en `parse_warnings`.

---

## 12. Perfil BBVA v1

Archivo:

```text
profiles/bbva_maestra_pyme.v1.profile.json
```

```json
{
  "bank_profile": "bbva_maestra_pyme",
  "profile_version": "v1",
  "bank_name": "BBVA",
  "detect_markers": ["MAESTRA PYME", "COD. DESCRIPCIÓN"],
  "anchor_regex": "^(\\d{2}/[A-Z]{3})\\s+(\\d{2}/[A-Z]{3})(.*)",
  "date_format": "%d/%b",
  "year_source": "periodo_header",
  "amount_strategy": "cargo_abono_two_columns",
  "saldo_columns": ["saldo_operacion", "saldo_liquidacion"],
  "saldo_not_on_every_row": true,
  "rastreo_regex": "(?:CVE\\s*RAST(?:REO)?|CLAVE\\s*DE\\s*RASTREO)\\s*[:\\s]+([A-Za-z0-9]+)",
  "referencia_regex": "Ref\\.\\s*([A-Za-z0-9]+)",
  "summary_deposits_regex": "Dep[oó]sitos\\s*/\\s*Abonos\\s*\\(\\+\\)\\s*\\$?\\s*([0-9,]+\\.\\d{2})",
  "summary_withdrawals_regex": "Retiros\\s*/\\s*Cargos\\s*\\(-\\)\\s*\\$?\\s*([0-9,]+\\.\\d{2})"
}
```

Reglas BBVA:

- La primera fecha es `transaction_date`.
- La segunda fecha es `posting_date`.
- `line_date = posting_date`.
- El saldo puede ser null sin marcar error.
- El año se resuelve desde el periodo del estado de cuenta.

---

## 13. Engine genérico de extracción

Flujo obligatorio de `bank_statement_extract`:

1. Resolver contexto.
2. Recibir `file_path` o `pdf_content`.
3. Calcular `file_hash` SHA256.
4. Extraer texto nativo del PDF.
5. Si el texto es insuficiente, clasificar como `requires_ocr`.
6. Detectar perfil si no fue recibido.
7. Cargar perfil JSON correspondiente.
8. Extraer metadata del documento:
   - banco
   - cuenta enmascarada
   - periodo inicio
   - periodo fin
9. Dividir texto en líneas.
10. Detectar líneas ancla.
11. Construir bloques multi-línea.
12. Parsear cada bloque según el perfil.
13. Normalizar fechas.
14. Normalizar signo del monto.
15. Extraer referencia y clave de rastreo.
16. Calcular `confidence` por línea.
17. Calcular totales extraídos.
18. Extraer totales reportados del resumen.
19. Validar diferencias.
20. Si `dry_run=true`, regresar preview sin escribir.
21. Si `dry_run=false`, guardar PDF en Storage si no existe.
22. Insertar `statement_extractions`.
23. Insertar `statement_extracted_lines`.
24. Regresar resultado.

---

## 14. Detección de PDF sin texto / OCR futuro

Si el texto extraído tiene menos de 500 caracteres, el documento se considera no procesable por v1.

Resultado:

```json
{
  "ok": false,
  "error": "requires_ocr",
  "data": {
    "source_format": "pdf",
    "text_length": 0,
    "supported_in_v1": false
  }
}
```

Si `dry_run=false`, puede registrarse una extracción con:

```text
status='requires_ocr'
validation_status='no_validable'
```

No se crean líneas.

---

## 15. Signo del monto

Regla universal:

```text
depósito / abono => amount positivo
retiro / cargo   => amount negativo
```

Además se guarda `direction`:

```text
deposito
retiro
```

Nunca se debe depender únicamente del signo después del parseo.

La dirección debe determinarse desde el layout/perfil:

- Banorte: estrategia declarada en perfil.
- BBVA: columna cargo/abono.

---

## 16. Fechas

Campos por línea:

```text
transaction_date
posting_date
line_date
```

### 16.1 Banorte

Si solo existe una fecha:

```text
transaction_date = fecha única
posting_date = fecha única
line_date = fecha única
```

### 16.2 BBVA

```text
transaction_date = primera fecha
posting_date = segunda fecha
line_date = posting_date
```

`line_date` es la fecha principal que usará reconciliation para matching inicial.

---

## 17. Validación de calidad

Antes de marcar una extracción como limpia, se validan mínimos y totales.

### 17.1 Mínimos obligatorios

Si cualquiera falla, `status='con_errores'`:

- `bank_profile` válido
- `total_blocks_detected > 0`
- `total_lines_extracted > 0`
- `statement_period_start` detectado cuando el perfil lo permite
- `statement_period_end` detectado cuando el perfil lo permite
- `account_number_mask` detectado cuando el perfil lo permite

### 17.2 Validación de depósitos

Comparar:

```text
total_deposits_extracted
vs
total_deposits_reported
```

Tolerancia:

```text
±0.01
```

Si la diferencia supera la tolerancia:

```text
validation_status='con_diferencias'
status='con_errores'
```

### 17.3 Validación de retiros/cargos

Comparar:

```text
abs(total_withdrawals_extracted)
vs
total_withdrawals_reported
```

Tolerancia:

```text
±0.01
```

Si la diferencia supera la tolerancia:

```text
validation_status='con_diferencias'
status='con_errores'
```

### 17.4 Resumen no encontrado

Si no se detectan totales reportados en el resumen:

```text
validation_status='no_validable'
status='con_errores'
```

No se debe marcar como extracción limpia.

---

## 18. Confidence y warnings

Cada línea extraída debe incluir:

```text
confidence
parse_warnings
```

### 18.1 Confidence

`confidence` representa la confianza del parser para esa línea.

Escala:

```text
1.0000 = parseo completo sin advertencias
0.8000 = parseo correcto con advertencias menores
0.5000 = parseo parcial
<0.5000 = línea dudosa
```

### 18.2 Warnings por línea

Ejemplos:

```json
[
  "saldo_no_detectado",
  "referencia_no_detectada",
  "clave_rastreo_no_detectada",
  "descripcion_multilinea_incompleta"
]
```

### 18.3 Warnings por extracción

La tabla `statement_extractions.warnings` agrega advertencias globales:

```json
[
  "resumen_no_detectado",
  "periodo_no_detectado",
  "diferencia_depositos",
  "diferencia_retiros"
]
```

---

## 19. Skills

### 19.1 `bank_statement_detect_profile`

Input:

```text
text_sample
```

Output exitoso:

```json
{
  "ok": true,
  "data": {
    "bank_profile": "bbva_maestra_pyme",
    "profile_version": "v1",
    "confidence": 0.98
  }
}
```

Output sin match:

```json
{
  "ok": false,
  "error": "perfil no soportado o PDF sin texto nativo suficiente"
}
```

---

### 19.2 `bank_statement_extract`

Input:

```text
file_path o pdf_content
bank_profile opcional
dry_run boolean default true
```

Reglas:

- v1 solo acepta PDF.
- Si `dry_run=true`, no escribe nada.
- Si `dry_run=false`, aplica idempotencia por `bank_profile + file_hash`.
- Si `dry_run=false`, guarda PDF original en Storage si no existe.
- Si el PDF requiere OCR, no crea líneas.

Output dry run:

```json
{
  "ok": true,
  "data": {
    "dry_run": true,
    "bank_profile": "banorte_enlace_global",
    "profile_version": "v1",
    "bank_name": "Banorte",
    "account_number_mask": "****1234",
    "statement_period_start": "2026-01-01",
    "statement_period_end": "2026-01-31",
    "total_blocks_detected": 40,
    "total_lines_preview": 5,
    "date_range_detected": {
      "min": "2026-01-02",
      "max": "2026-01-31"
    },
    "validation": {
      "total_deposits_reported": 100000.00,
      "total_deposits_extracted": 100000.00,
      "validation_diff_deposits": 0.00,
      "total_withdrawals_reported": 85000.00,
      "total_withdrawals_extracted": 85000.00,
      "validation_diff_withdrawals": 0.00,
      "validation_status": "validado"
    },
    "preview_lines": []
  }
}
```

Output real:

```json
{
  "ok": true,
  "data": {
    "dry_run": false,
    "idempotent": false,
    "extraction": {},
    "lines_created": 40
  }
}
```

---

### 19.3 `bank_statement_profile_learn`

Input:

```text
text_sample
column_mapping confirmado por humano
```

Reglas:

- Crea un perfil nuevo en estado `borrador`.
- Nunca se activa automáticamente.
- Nunca se usa en extracción real hasta que sea marcado manualmente como activo.
- Sirve para preparar fase 2 o nuevos bancos.

Output:

```json
{
  "ok": true,
  "data": {
    "profile_path": "profiles/nuevo_banco.v1.profile.json",
    "status": "borrador"
  }
}
```

---

### 19.4 `bank_statement_to_excel`

Input:

```text
extraction_id
```

Output:

```text
archivo .xlsx descargable
```

Debe validar que la extracción pertenece al contexto de empresa resuelto.

---

## 20. Exportación Excel

El Excel debe tener dos hojas.

### 20.1 Hoja `Movimientos`

Columnas:

- folio
- raw_line_order
- line_date
- transaction_date
- posting_date
- description
- direction
- amount
- saldo
- clave_rastreo
- referencia
- confidence
- parse_warnings
- raw_text

### 20.2 Hoja `Resumen`

Columnas/campos:

- extraction_folio
- bank_profile
- profile_version
- bank_name
- account_number_mask
- statement_period_start
- statement_period_end
- file_name
- file_hash
- storage_bucket
- storage_path
- validation_status
- status
- total_deposits_reported
- total_deposits_extracted
- validation_diff_deposits
- total_withdrawals_reported
- total_withdrawals_extracted
- validation_diff_withdrawals
- warnings

---

## 21. Relación con `vertical_erp_reconciliation`

Este vertical no escribe en `banks_movements`.

`vertical_erp_reconciliation` leerá:

```text
statement_extractions
statement_extracted_lines
```

Campos principales para matching:

```text
clave_rastreo
referencia
amount
line_date
posting_date
account_number_mask
```

La decisión de crear movimientos faltantes vive en `vertical_erp_reconciliation`, no aquí.

Si reconciliation crea un movimiento faltante, debe hacerlo a través de `vertical_erp_banks` y sus reglas de autorización.

---

## 22. Relación con `vertical_erp_banks`

No hay escritura directa a Banks.

Prohibido en este vertical:

- insertar en `banks_movements`
- actualizar saldos
- marcar conciliado
- crear ajustes bancarios
- autorizar movimientos

Banks es consumidor indirecto vía Reconciliation.

Cadena correcta:

```text
Bank Statement Converter
  ↓
ERP Reconciliation
  ↓
ERP Banks
```

---

## 23. Patrón de archivos por skill

Seguir el patrón ERP actual:

```text
<skill_name>/
  manifest.json
  skill.py
  service.py
```

Skills:

```text
bank_statement_detect_profile/
bank_statement_extract/
bank_statement_profile_learn/
bank_statement_to_excel/
```

Además:

```text
vertical_bank_statement_converter/
  _statement_common.py
  profiles/
    banorte_enlace_global.v1.profile.json
    bbva_maestra_pyme.v1.profile.json
```

Registrar todos los skills en:

```text
factory/skills/registry.json
```

---

## 24. Casos de prueba mínimos

- [ ] Detectar perfil Banorte.
- [ ] Detectar perfil BBVA.
- [ ] Rechazar PDF sin texto nativo suficiente.
- [ ] Marcar `requires_ocr` para PDF escaneado.
- [ ] Agrupar correctamente bloques multi-línea.
- [ ] Extraer clave de rastreo.
- [ ] Extraer referencia.
- [ ] Banorte: saldo presente en cada línea.
- [ ] Banorte: warning si falta saldo donde se esperaba.
- [ ] BBVA: permitir `saldo=null`.
- [ ] BBVA: separar `transaction_date` y `posting_date`.
- [ ] Validar depósitos contra resumen.
- [ ] Validar retiros contra resumen.
- [ ] Marcar `con_errores` si los totales no cuadran.
- [ ] Marcar `no_validable` si no se detecta resumen.
- [ ] Idempotencia: mismo PDF no duplica extracción.
- [ ] Storage: mismo PDF no duplica archivo.
- [ ] Exportar Excel con hoja `Movimientos`.
- [ ] Exportar Excel con hoja `Resumen`.
- [ ] Confirmar que no escribe en `banks_movements`.
- [ ] Confirmar que cada skill valida schema/empresa antes de leer o escribir.

---

## 25. Checklist final de diseño para codificación

1. Schema por empresa.
2. Resolver contexto con `resolve_statement_context`.
3. Crear migración SQL de `statement_extractions` y `statement_extracted_lines`.
4. Usar folios `BSE` y `BSL` con `reserve_erp_folio()`.
5. Guardar PDF original en Supabase Storage.
6. Guardar `storage_bucket`, `storage_path` y `file_hash`.
7. Implementar idempotencia por `bank_profile + file_hash`.
8. Crear perfiles versionados Banorte y BBVA.
9. Implementar engine genérico de bloques multi-línea.
10. Implementar parser por estrategia de perfil.
11. Implementar validación de depósitos.
12. Implementar validación de retiros.
13. Implementar status `requires_ocr`.
14. Implementar `confidence` y `parse_warnings`.
15. Implementar exportación Excel con hoja `Movimientos` y `Resumen`.
16. Registrar skills en `factory/skills/registry.json`.
17. Probar contra PDFs reales de Banorte y BBVA.
18. No implementar OCR en v1.
19. No escribir en ERP Banks.
20. Mantener separación total con Reconciliation.

---

## 26. Estado del diseño

Diseño v1 cerrado para arquitectura.

Este documento queda como referencia única para implementar `vertical_bank_statement_converter` v1.

No se reabre el alcance v1 salvo que aparezca un bug bloqueante en PDFs reales de Banorte o BBVA.
