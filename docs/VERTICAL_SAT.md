# vertical_sat

Descarga, parseo y almacenamiento de CFDIs (Comprobantes Fiscales Digitales por Internet) del SAT México via el servicio de **Descarga Masiva**.

Permite bajar facturas emitidas (ventas / ingresos) y recibidas (compras / gastos) de forma automatizada, guardarlas en Supabase y consultarlas desde el dashboard.

---

## Flujo maestro

```
credenciales e.firma + RFC + rango de fechas
         │
         ▼
    sat_auth          →  token SOAP (válido 5 min)
         │
         ▼
sat_cfdi_solicitud    →  id_solicitud (SAT procesa en segundo plano)
         │
         ▼
sat_cfdi_verificar    →  poll cada 15 s hasta estado 5000 → ids de paquetes
  (hasta 20 intentos)
         │
         ▼ (por cada paquete)
sat_cfdi_descargar    →  ZIP base64 → lista de strings XML
         │
         ▼
sat_cfdi_parser       →  dict estructurado por CFDI (uuid, rfcs, total, conceptos…)
         │
         ▼
sat_cfdi_store        →  upsert en Supabase cfdi_documentos (dedup por uuid_cfdi)
         │
         ▼
sat_cfdi_list         →  dashboard / consulta filtrable
```

**Orquestador**: `sat_cfdi_sync` ejecuta todo lo anterior en una sola llamada.

---

## Skills

| # | Skill | Descripción | Requiere firma |
|---|-------|-------------|:--------------:|
| 1 | `sat_auth` | Autenticación SOAP con WS-Security + XML-DSig → token 5 min | ✅ |
| 2 | `sat_cfdi_solicitud` | Solicita paquete de descarga (fechas, tipo E/R) → id_solicitud | ✅ |
| 3 | `sat_cfdi_verificar` | Poll estado solicitud → lista de ids de paquetes listos | ✅ |
| 4 | `sat_cfdi_descargar` | Descarga paquete ZIP → lista de XMLs de CFDIs | ✅ |
| 5 | `sat_cfdi_parser` | Parsea XML CFDI 3.3 / 4.0 → dict estructurado | — |
| 6 | `sat_cfdi_store` | Upsert en Supabase `cfdi_documentos` (dedup por uuid) | — |
| 7 | `sat_cfdi_sync` | **Orquestador completo** — una llamada hace todo | ✅ |
| 8 | `sat_cfdi_list` | `kind=data` — lista/filtra CFDIs para dashboard | — |

---

## Env vars requeridas

| Variable | Descripción |
|----------|-------------|
| `SAT_RFC` | RFC del contribuyente (ej. `XAXX010101000`) |
| `SAT_EFIRMA_CER_B64` | Certificado `.cer` codificado en base64 |
| `SAT_EFIRMA_KEY_B64` | Llave privada `.key` codificada en base64 |
| `SAT_EFIRMA_PASSWORD` | Contraseña de la llave privada |

### Cómo convertir e.firma a base64

```bash
# En Linux / Mac
base64 -w0 mi_firma.cer > cer_b64.txt
base64 -w0 mi_firma.key > key_b64.txt

# En Windows (PowerShell)
[Convert]::ToBase64String([IO.File]::ReadAllBytes("mi_firma.cer")) | Out-File cer_b64.txt
[Convert]::ToBase64String([IO.File]::ReadAllBytes("mi_firma.key")) | Out-File key_b64.txt
```

Pega el contenido de cada archivo como valor de la env var en Render.

---

## Dependencias Python

```
cryptography==44.0.3   # firmar XML con llave privada RSA (PKCS1v15 + SHA1)
lxml==5.3.1            # construir / parsear SOAP + CFDI XML + exc-C14N
```

Ya incluidas en `requirements.txt`.

---

## Endpoints SAT (Descarga Masiva)

| Operación | URL |
|-----------|-----|
| Autenticación | `https://cfdidescargamasiva.clouda.sat.gob.mx/Autenticacion/Autenticacion.svc` |
| SolicitaDescarga | `https://cfdidescargamasiva.clouda.sat.gob.mx/SolicitaDescargaService.svc` |
| VerificaSolicitud | `https://cfdidescargamasiva.clouda.sat.gob.mx/VerificaSolicitudDescargaService.svc` |
| DescargarPaquete | `https://cfdidescargamasiva.clouda.sat.gob.mx/DescargarPaqueteService.svc` |

---

## Tabla Supabase: `cfdi_documentos`

```sql
CREATE TABLE cfdi_documentos (
  id               uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  uuid_cfdi        text        UNIQUE NOT NULL,
  tipo             text        NOT NULL,          -- 'E' emitido, 'R' recibido
  rfc_emisor       text,
  nombre_emisor    text,
  rfc_receptor     text,
  nombre_receptor  text,
  fecha_emision    date,
  fecha_timbrado   timestamptz,
  total            numeric,
  subtotal         numeric,
  descuento        numeric     DEFAULT 0,
  moneda           text        DEFAULT 'MXN',
  tipo_comprobante text,       -- I=ingreso E=egreso T=traslado N=nomina P=pago
  metodo_pago      text,
  forma_pago       text,
  uso_cfdi         text,
  estado           text        DEFAULT 'vigente', -- vigente, cancelado
  conceptos        jsonb,
  xml_raw          text,
  rfc_propietario  text,       -- RFC de quien descargó
  created_at       timestamptz DEFAULT now()
);

-- Índices recomendados
CREATE INDEX idx_cfdi_tipo          ON cfdi_documentos (tipo);
CREATE INDEX idx_cfdi_rfc_prop      ON cfdi_documentos (rfc_propietario);
CREATE INDEX idx_cfdi_fecha         ON cfdi_documentos (fecha_emision);
CREATE INDEX idx_cfdi_rfc_emisor    ON cfdi_documentos (rfc_emisor);
CREATE INDEX idx_cfdi_rfc_receptor  ON cfdi_documentos (rfc_receptor);
```

Crea la tabla desde el dashboard en **Supabase → SQL Editor** o con `supabase_sql_execute`.

---

## Contratos de skills

### `sat_auth`

**Input:**
```python
{
  "dry_run": False,
  # Opcionales — si no se pasan, toma de env vars
  "rfc":          "XAXX010101000",
  "cer_b64":      "<base64 del .cer>",
  "key_b64":      "<base64 del .key>",
  "key_password": "mipassword",
}
```

**Output:**
```python
{"ok": True, "message": "Token SAT obtenido",
 "data": {"token": "eyJ...", "rfc": "XAXX010101000"}}
```

---

### `sat_cfdi_solicitud`

**Input:**
```python
{
  "token":           "<token de sat_auth>",
  "rfc":             "XAXX010101000",
  "fecha_inicio":    "2025-01-01",   # YYYY-MM-DD
  "fecha_fin":       "2025-01-31",
  "tipo":            "E",            # E=emitidos, R=recibidos
  "tipo_comprobante": "",            # "" = todos, I/E/T/N/P
  "dry_run": False,
}
```

**Output:**
```python
{"ok": True, "message": "Solicitud aceptada: abc123-...",
 "data": {"id_solicitud": "abc123-...", "tipo": "E", "rfc": "XAXX..."}}
```

---

### `sat_cfdi_verificar`

**Input:**
```python
{
  "token":        "<token>",
  "rfc":          "XAXX010101000",
  "id_solicitud": "abc123-...",
  "dry_run": False,
}
```

**Output:**
```python
{"ok": True,
 "data": {
   "cod_estado":   "5000",
   "estado":       "Terminada",
   "listo":        True,
   "esperar":      False,
   "vacio":        False,
   "paquetes":     ["pkg-001", "pkg-002"],
   "id_solicitud": "abc123-...",
 }}
```

**Códigos de estado SAT:**

| Código | Significado | Acción |
|--------|-------------|--------|
| `5000` | Terminada — paquetes listos | Descargar |
| `5001` | Aceptada — en cola | Esperar |
| `5002` | En proceso | Esperar |
| `5003` | Terminada sin datos | No hay CFDIs en ese rango |
| `5004` / `5005` | Error / Rechazada | Revisar parámetros |

---

### `sat_cfdi_descargar`

**Input:**
```python
{
  "token":      "<token>",
  "rfc":        "XAXX010101000",
  "id_paquete": "pkg-001",
  "dry_run": False,
}
```

**Output:**
```python
{"ok": True, "message": "150 XMLs extraídos del paquete",
 "data": {"xmls": ["<?xml...", ...], "total": 150, "id_paquete": "pkg-001"}}
```

---

### `sat_cfdi_parser`

**Input (un XML):**
```python
{"xml": "<?xml version='1.0'...<cfdi:Comprobante..."}
```

**Input (lote):**
```python
{"xmls": ["<?xml...", "<?xml...", ...]}
```

**Output:**
```python
{"ok": True, "data": {"cfdis": [
  {
    "uuid":             "6128FB46-...",
    "version":          "4.0",
    "tipo_comprobante": "I",
    "fecha_emision":    "2025-01-15T10:30:00",
    "fecha_timbrado":   "2025-01-15T10:30:45",
    "serie":            "A",
    "folio":            "1234",
    "subtotal":         "5000.00",
    "descuento":        "0",
    "total":            "5800.00",
    "moneda":           "MXN",
    "tipo_cambio":      "1",
    "metodo_pago":      "PUE",
    "forma_pago":       "03",
    "uso_cfdi":         "G01",
    "rfc_emisor":       "XAXX010101000",
    "nombre_emisor":    "Mi Empresa SA de CV",
    "rfc_receptor":     "YYYY010101000",
    "nombre_receptor":  "Cliente SA de CV",
    "conceptos":        [{"descripcion": "Servicio", "cantidad": "1", "importe": "5000.00", ...}],
    "xml_raw":          "<?xml...",
  }
]}}
```

---

### `sat_cfdi_store`

**Input:**
```python
{
  "cfdis":           [<lista de dicts de sat_cfdi_parser>],
  "tipo":            "E",            # E o R — se guarda en campo tipo
  "rfc_propietario": "XAXX010101000",
  "dry_run": False,
}
```

**Output:**
```python
{"ok": True, "message": "150 CFDIs guardados en Supabase",
 "data": {"insertados": 150, "total": 150}}
```

---

### `sat_cfdi_sync` (orquestador)

**Input:**
```python
{
  "rfc":             "XAXX010101000",  # o SAT_RFC env var
  "fecha_inicio":    "2025-01-01",
  "fecha_fin":       "2025-01-31",
  "tipo":            "E",              # E=emitidos, R=recibidos
  "tipo_comprobante": "",              # vacío = todos
  "dry_run": False,
}
```

**Output:**
```python
{"ok": True,
 "message": "145 CFDIs guardados (E, 2025-01-01→2025-01-31)",
 "data": {
   "cfdis_guardados": 145,
   "paquetes":        2,
   "id_solicitud":    "abc123-...",
   "log": [
     {"paso": "sat_auth",           "ok": True,  "msg": "Token SAT obtenido"},
     {"paso": "sat_cfdi_solicitud", "ok": True,  "msg": "Solicitud aceptada: abc123"},
     {"paso": "sat_cfdi_verificar#1","ok": True, "msg": "Estado 5002 — En proceso — 0 paquetes"},
     {"paso": "sat_cfdi_verificar#2","ok": True, "msg": "Estado 5000 — Terminada — 2 paquetes"},
     {"paso": "sat_cfdi_descargar:pkg-001","ok": True, "msg": "100 XMLs extraídos"},
     {"paso": "sat_cfdi_parser",    "ok": True,  "msg": "100 parseados, 0 errores"},
     {"paso": "sat_cfdi_store",     "ok": True,  "msg": "100 CFDIs guardados"},
     ...
   ],
 }}
```

---

### `sat_cfdi_list` (kind=data)

**Input (query params o context):**
```python
{
  "tipo":             "E",              # E=emitidos, R=recibidos, ""=todos
  "rfc_propietario":  "XAXX010101000",  # o SAT_RFC env var
  "mes":              "2025-01",        # YYYY-MM — mutuamente excluyente con dia
  "dia":              "2025-01-15",     # YYYY-MM-DD
  "limit":            500,
}
```

**Output:**
```python
{"ok": True, "message": "145 CFDIs",
 "data": {
   "cfdis":           [<lista de registros de cfdi_documentos>],
   "total":           145,
   "total_ingresos":  145,
   "total_egresos":   0,
   "monto_total":     843500.00,
   "filtros":         {"tipo": "E", "mes": "2025-01", "dia": "", "rfc": "XAXX..."},
 }}
```

---

## Dashboard SAT

Página **SAT** en el dashboard con:

- **Header**: RFC configurado, estado e.firma, estado credenciales
- **Descargar CFDIs**: expander con fecha inicio/fin, tipo (E/R/Ambos), tipo comprobante → botón "Sincronizar con SAT" (deshabilitado si no hay creds)
- **CFDIs Emitidos**: tabla filtrable por mes o día con métricas (total, monto, tipo I)
- **CFDIs Recibidos**: tabla filtrable por mes o día con métricas (total, monto, tipo E)

---

## Pasos para activar

1. **Obtener e.firma** — descarga desde [sat.gob.mx](https://www.sat.gob.mx/tramites/11331/renueva-el-certificado-de-e.firma)
2. **Convertir a base64** (ver sección Env Vars arriba)
3. **Configurar env vars** en Render: `SAT_RFC`, `SAT_EFIRMA_CER_B64`, `SAT_EFIRMA_KEY_B64`, `SAT_EFIRMA_PASSWORD`
4. **Crear tabla** `cfdi_documentos` en Supabase (SQL arriba)
5. **Deploy** en Render — Render instalará `cryptography` y `lxml` automáticamente
6. **Primera prueba**: Dashboard → SAT → Descargar CFDIs → mes actual → Emitidos → Sincronizar

---

## Notas técnicas

- El token SAT tiene **vigencia de 5 minutos**. `sat_cfdi_sync` lo obtiene al inicio y lo usa para toda la sesión. Si el proceso tarda más, obtener token fresco antes de descargar.
- El SAT puede tardar **varios minutos** en preparar el paquete. `sat_cfdi_verificar` hace poll máx 20 veces cada 15 s (5 min total). Para rangos grandes puede tardar más — aumentar `_POLL_MAX` en `sat_cfdi_verificar/service.py`.
- Cada paquete ZIP contiene hasta **200 CFDIs**. Un mes con muchas facturas genera múltiples paquetes.
- La firma XML usa **RSA-SHA1 + PKCS1v15** — es el estándar del SAT (no SHA256).
- `sat_cfdi_store` usa `Prefer: resolution=merge-duplicates` — hacer re-sync del mismo mes no duplica registros.
- El campo `tipo` en `cfdi_documentos` refleja la perspectiva del solicitante: `E` = yo emití la factura (ingreso para mí), `R` = yo recibí la factura (gasto para mí). El campo `tipo_comprobante` del CFDI mismo (I/E/T/N/P) se guarda en `tipo_comprobante`.
