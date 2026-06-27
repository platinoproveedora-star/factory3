# Conta4all — Contexto completo para Claude Code

## Qué es Conta4all
SaaS para contadores mexicanos que descarga facturas CFDI del SAT automáticamente y las presenta en un dashboard limpio por empresa. Cliente actual: UC-102.

## Stack
- **Backend skills**: Factory3 (Python, Render) — `factory/skills/internos/vertical_sat/`
- **DB**: Supabase, schema `uc102_proy001`
- **Dashboard actual**: Streamlit en Render (funcional, prototipo)
- **Dashboard nuevo**: Next.js en Vercel (por construir)
- **Auth SAT**: e.firma (.cer + .key + password) → token WRAP

---

## Skills SAT — todos funcionando, NO modificar sin razón

| Skill | Función |
|---|---|
| `sat_auth` | Obtiene token del SAT con e.firma |
| `sat_cfdi_solicitud` | Crea solicitud de descarga masiva SOAP |
| `sat_cfdi_verificar` | Polling de estado de solicitud (EstadoSolicitud 0-6) |
| `sat_cfdi_descargar` | Descarga ZIPs de paquetes |
| `sat_cfdi_parse` | Parsea XMLs de CFDIs dentro del ZIP |
| `sat_cfdi_store` | Upsert CFDIs en Supabase (dedup por empresa_id+uuid_cfdi) |
| `sat_cfdi_list` | Lista CFDIs desde Supabase para dashboard (kind=data) |
| `sat_cfdi_sync` | **Orquesta TODO el flujo completo** de una sola llamada |
| `sat_solicitud_manager` | Persiste solicitudes en DB entre sesiones |

### sat_cfdi_sync — flujo completo
`sat_auth` → `sat_cfdi_solicitud` → polling `sat_cfdi_verificar` → `sat_cfdi_descargar` → `sat_cfdi_parse` → `sat_cfdi_store`

### Parámetros clave de context
```python
{
  "rfc":           "RFC_EMPRESA",       # siempre UPPERCASE
  "empresa_id":    "RFC_EMPRESA",
  "rfc_propietario": "RFC_EMPRESA",
  "cer_b64":       "...",               # NUNCA guardar en DB ni logs
  "key_b64":       "...",               # NUNCA guardar en DB ni logs
  "key_password":  "...",               # NUNCA guardar en DB ni logs
  "fecha_inicio":  "YYYY-MM-DD",
  "fecha_fin":     "YYYY-MM-DD",
  "tipo":          "E",                 # E=emitidos/ingresos, R=recibidos/egresos
  "tipo_solicitud": "CFDI",
  "schema":        "uc102_proy001",
  "dry_run":       False,
}
```

### Credenciales multi-empresa (env vars Render)
```
EMPRESA_1_RFC=...
EMPRESA_1_CER_B64=...
EMPRESA_1_KEY_B64=...
EMPRESA_1_PWD=...
EMPRESA_2_RFC=...
# ... hasta EMPRESA_9
```
Las credenciales (.key, .cer, password) **NUNCA** se almacenan en Supabase ni logs.

---

## Supabase — schema `uc102_proy001`

### `cfdi_documentos`
```sql
id, empresa_id, uuid_cfdi (UNIQUE juntos),
tipo (E/R), rfc_emisor, nombre_emisor, rfc_receptor, nombre_receptor,
fecha_emision (date), fecha_timbrado, total, subtotal, descuento,
moneda, tipo_comprobante, metodo_pago, forma_pago, uso_cfdi,
conceptos (jsonb), xml_raw, rfc_propietario, created_at
```

### `sat_solicitudes`
```sql
id, empresa_id, rfc, id_solicitud, tipo (E/R), tipo_solicitud,
fecha_inicio, fecha_fin, estado (0-6), paquetes, num_cfdis,
created_at, updated_at
```

**EstadoSolicitud SAT:** 0=Pendiente, 1=Aceptada, 2=En proceso, 3=Terminada, 4=Error, 5=Rechazada, 6=Vencida

---

## Dashboard Streamlit actual
**Ruta**: `companies/EMP_CONTA4ALL/projects/PROY-001_SAT/dashboard/app.py`

4 pestañas:
- **Sincronizar**: carga e.firma, selecciona periodo, botones solicitar/verificar
- **Solicitudes**: historial desde `sat_solicitud_manager`
- **Ingresos** (tipo=E): CFDIs emitidos, agrupados por mes con expanders, búsqueda full-text
- **Egresos** (tipo=R): CFDIs recibidos, mismo formato

Funciona pero es prototipo Streamlit — no es sellable.

---

## Dashboard Next.js nuevo — por construir

**Objetivo**: misma funcionalidad, diseño sellable, multi-empresa.

### UX simplificada (key change)
En vez de dos pasos (Solicitar → Verificar/Descargar), **un solo botón "Sincronizar"** que:
1. Llama `sat_cfdi_sync` vía Factory API
2. Muestra progreso en tiempo real: `Solicitando → SAT procesando → Descargando → Guardando → Listo ✓`
3. Si SAT tarda más de 60s (timeout Vercel), el estado queda en `sat_solicitudes` y el usuario puede volver después — el dashboard lo retoma automáticamente

### Páginas
1. **Dashboard / Overview**: métricas del año (total ingresos, egresos, top proveedores, top clientes)
2. **Sincronizar**: selector empresa + periodo + botón único
3. **Ingresos**: tabla por mes colapsable, búsqueda, exportar CSV
4. **Egresos**: ídem
5. **Solicitudes**: historial con estados

### API que consume
- `POST /run/vertical_sat/sat_cfdi_sync` — sincronización
- `GET /data/vertical_sat/sat_cfdi_list?tipo=E&...` — listar CFDIs
- `GET /data/vertical_sat/sat_solicitud_manager?action=list&...` — solicitudes

### Credenciales
- Si hay env vars → no muestra uploader
- Si no hay env vars → muestra upload .cer / .key

---

## Fixes críticos aprendidos (NO repetir)

| Error | Causa real | Fix |
|---|---|---|
| 301 "No se permite cancelados" | Falta `EstadoComprobante="Vigente"` | Siempre incluirlo, para E y R |
| 500 "Error deserializing" | `RfcEmisor` no existe en schema de Emitidos | Solo usar en Recibidos como filtro |
| 403 Supabase | Schema no expuesto o sin GRANT | `sat_cfdi_store action=setup` |
| 409 duplicate key | PostgREST sin `on_conflict` explícito | `?on_conflict=empresa_id,uuid_cfdi` |
| CFDIs vacíos en list | Faltaba `Accept-Profile: uc102_proy001` | Header obligatorio en todas las queries |
| 301 en verificar | RFC en minúscula | RFC siempre `.strip().upper()` antes de usarse |
| EstadoSolicitud=0 | SAT no ha registrado la solicitud aún | Incluir 0 en `_ESTADO_ESPERAR`, reintentar |

---

## Pendiente
- [ ] RFC uppercase en dashboard (hecho en código, pendiente commit junto con otros cambios)
- [ ] Nuevo dashboard Next.js en Vercel
- [ ] Commit general de todos los cambios de esta sesión
