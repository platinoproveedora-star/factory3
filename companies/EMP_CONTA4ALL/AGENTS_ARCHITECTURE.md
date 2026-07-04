# Arquitectura de Agentes — EMP_CONTA4ALL

- **company_id:** `EMP_CONTA4ALL`
- **client_id:** `UC-102`
- **Tipo:** service_company — SaaS contable multi-RFC

---

## Estado de arquitectura

| Versión | Estado | DB | Dashboard |
|---|---|---|---|
| v1 prototipo (PROY-001) | Funcional, legado | `uc102_proy001` Supabase interno | Streamlit en Render |
| **v2 plataforma** (en construcción) | En desarrollo | Supabase **nuevo y dedicado** (`PLATFORM_*`) | Next.js en Vercel |

---

## v1 — Prototipo Streamlit (legado, no modificar)

```
Usuario (Streamlit) → sube e.firma → sat_cfdi_sync (bloqueante, hasta 15min)
                                           ↓
                              cfdi_documentos (uc102_proy001)
                                           ↓
                              sat_cfdi_list → tablas Ingresos/Egresos
```

Skills usados: todos de `vertical_sat/` (sat_auth, sat_cfdi_solicitud, sat_cfdi_verificar,
sat_cfdi_descargar, sat_cfdi_parser, sat_cfdi_store, sat_cfdi_list, sat_cfdi_sync).

---

## v2 — Plataforma pública (en construcción)

### Supabase dedicado (PLATFORM_*)

Proyecto Supabase **nuevo y separado** del Supabase interno de Factory3.

Env vars en Render y Vercel:
```
PLATFORM_SUPABASE_URL
PLATFORM_SUPABASE_SERVICE_ROLE_KEY
PLATFORM_SUPABASE_ACCESS_TOKEN
PLATFORM_SUPABASE_PROJECT_REF
PLATFORM_KEK_V1                    ← KEK maestra para cifrado DEK/AES-256-GCM, NUNCA en Supabase
```

### Schemas en el Supabase dedicado

**`platform`** — identidad compartida entre todos los módulos públicos futuros:
```sql
platform.users            -- email, password_hash (Argon2id), nombre
platform.modulos          -- code PK ("conta4all", "expenses4all", ...)
platform.access_grants    -- user_id + modulo_code + role (owner/platform_admin)
platform.secrets          -- vault cifrado DEK/KEK por managed_rfc_id
platform.password_resets
platform.login_attempts   -- throttling por email + IP
```

**`conta4all`** — datos del módulo, multi-tenant por fila:
```sql
conta4all.managed_rfcs      -- owner_user_id + rfc UNIQUE por owner
conta4all.cfdi_documentos   -- managed_rfc_id + uuid_cfdi UNIQUE
```

### Flujo v2

```
Browser (Next.js)
    │ cookie httpOnly JWT
    ▼
Next.js API Routes (mismo origen — NUNCA Factory API directo desde browser)
    │
    ├── POST /api/sync/start   → conta4all_sync_start  (sat_auth + sat_cfdi_solicitud)
    │                                                   → devuelve id_solicitud
    │
    ├── POST /api/sync/poll    → conta4all_sync_poll    (re-auth + 1x sat_cfdi_verificar)
    │                                                   → devuelve {listo, esperar, paquetes}
    │   (browser llama cada 15-20s mientras esperar=true)
    │
    └── POST /api/sync/poll    → conta4all_sync_finalize (sat_cfdi_descargar + parser + store)
        cuando listo=true                               → devuelve cfdis_guardados

Lectura:
    GET /api/cfdis?tipo=E&managed_rfc_id=... → conta4all_cfdi_list (kind=data)
```

### Skills nuevos — vertical_sat_conta4all

| Skill | Función | Llama a |
|---|---|---|
| `conta4all_cfdi_store` | Upsert en `conta4all.cfdi_documentos` por `managed_rfc_id` | PLATFORM_SUPABASE_* |
| `conta4all_cfdi_list` | Lista CFDIs por `managed_rfc_id` (kind=data) | PLATFORM_SUPABASE_* |
| `conta4all_sync_start` | Paso 1: auth + solicitud → id_solicitud | `vertical_sat/sat_auth`, `sat_cfdi_solicitud` |
| `conta4all_sync_poll` | Paso 2: re-auth + 1 verificación (sin loop) | `vertical_sat/sat_auth`, `sat_cfdi_verificar` |
| `conta4all_sync_finalize` | Paso 3: descargar + parsear + guardar | `vertical_sat/sat_cfdi_descargar`, `sat_cfdi_parser`, `conta4all_cfdi_store` |

Los skills de `vertical_sat/` originales **no se modifican** — los nuevos los invocan internamente.

### Skills pendientes — vertical_auth_security

| Skill | Función |
|---|---|
| `security_user_register` | email + password → Argon2id hash |
| `security_user_login` | JWT en cookie httpOnly (1-2h), throttling por email+IP |
| `security_user_session_verify` | valida JWT — middleware de dashboard |
| `security_managed_rfc_create/list/delete` | RFCs del usuario, validación regex SAT |
| `security_secret_store` | cifra e.firma (DEK/KEK) en `platform.secrets` |
| `security_secret_retrieve` | descifra — **SOLO server-to-server, bloqueado en /run/ HTTP** |
| `security_access_grant_create` | alta manual de acceso por módulo (sin Stripe v1) |
| `security_access_check` | ¿user tiene grant activo para este modulo_code? |
| `security_password_reset_request/_confirm` | sin envío de correo activo aún |
| `security_support_decrypt_session` | diseñado, sin UI conectada (requiere motivo + audit log) |

### Cifrado e.firma — Modelo A (recuperable)

```
e.firma del usuario (cer+key+password)
    │ DEK aleatoria 256-bit por secreto
    ▼ AES-256-GCM
payload_cifrado (jsonb en platform.secrets)
    │ DEK cifrada con KEK maestra
    ▼
dek_encrypted (en platform.secrets, nunca la DEK en claro)

KEK maestra = PLATFORM_KEK_V1 (env var Render — NUNCA en Supabase)
```

Descifrado: SOLO dentro de `security_secret_retrieve`, invocado por skills internos.
NUNCA en respuesta HTTP directa al browser.

### Seguridad transversal (requerida antes de salir a público)

- JWT: cookie httpOnly + secure + sameSite=strict (NUNCA localStorage)
- CORS factory_api.py: cerrado al dominio exacto del dashboard Conta4all
- Rate limiting en /api/sync/*, /api/cfdis, login — por cuenta Y por IP
- RFC siempre `.strip().upper()` antes de cualquier query
- `managed_rfc_id` validado como UUID antes de interpolar en filtros PostgREST
- Headers: CSP, X-Frame-Options: DENY, HSTS
- RLS activado en ambos schemas desde día 1
- Tamaño máximo .cer/.key: validar KBs + parsear como DER antes de aceptar

### Pendiente en este ciclo

- [ ] `vertical_auth_security` — 11 skills (ver tabla arriba)
- [ ] `supabase_project_create` — skill para crear el proyecto PLATFORM en Supabase
- [ ] `supabase_project_status_check` — polling de salud del proyecto
- [ ] Dashboard Next.js v1 — 5 pantallas (Login, Mis RFCs, Sincronizar, Ingresos/Egresos, Overview)
- [ ] Modificar `factory_api.py` — bloquear skills `internal_only: true` del endpoint `/run/`
- [ ] Crear tablas DDL en Supabase dedicado (`conta4all_cfdi_store action=setup_table`)
- [ ] Exponer schema `conta4all` en Data API del proyecto Supabase nuevo

### Diferido a Fase 2

- vertical_payments (Stripe): subscriptions, checkout, webhooks
- 2FA, captcha, Cloudflare/WAF
- Correo transaccional (registro, "romper cristal")
- security_audit_log con UI
- OXXO: solo soporta pago único en Stripe (no suscripción recurrente nativa)

---

## Nomenclatura

Usar siempre **`modulo_code`** / **`módulo`** — NUNCA `product_code`/`producto`.
Aplica a columnas, parámetros de skills, nombres de tabla y docs.

---

## Verificación antes de producción

```bash
factory_no_hardcode_audit   # 0 blockers en companies/EMP_CONTA4ALL/ + vertical_sat_conta4all/
qa_secrets_check            # PLATFORM_* vars presentes en Render y Vercel
conta4all_cfdi_store action=setup_table dry_run=False   # DDL aplicado en PLATFORM Supabase
```
