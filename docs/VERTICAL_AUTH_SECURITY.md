# vertical_auth_security — Referencia

Autenticación, vault de credenciales y control de acceso para módulos públicos de Factory3.
Todos los skills reciben `modulo_code` por context — nunca hardcodeado.

---

## Skills

| Skill | action | Descripción |
|---|---|---|
| `security_user_register` | — | Registro email+password (Argon2id) |
| `security_user_login` | — | Login → JWT 2h. Throttling por email+IP |
| `security_user_session_verify` | — | Valida JWT. Middleware de dashboard |
| `security_managed_rfc` | create / list / delete | CRUD de RFCs del usuario |
| `security_secret_store` | — | Cifra e.firma (DEK/AES-256-GCM + KEK) |
| `security_secret_retrieve` | — | **SOLO server-to-server** — descifra e.firma |
| `security_access_grant` | create / check / delete | Grants de acceso por módulo |
| `security_password_reset` | request / confirm | Reset sin correo en v1 |
| `security_support_decrypt_session` | — | **SOLO server-to-server** — romper cristal con motivo + audit log |

---

## Env vars requeridas

```
PLATFORM_SUPABASE_URL                ← URL del Supabase dedicado (no el interno de Factory3)
PLATFORM_SUPABASE_SERVICE_ROLE_KEY   ← service_role del Supabase dedicado
PLATFORM_JWT_SECRET                  ← string aleatorio >= 32 chars para firmar JWT
PLATFORM_KEK_V1                      ← 32 bytes hex (genera: python -c "import secrets; print(secrets.token_hex(32))")
```

---

## Flujo de registro + primera sincronización

```
1. security_user_register   email, password, password_confirm, nombre, modulo_code
        ↓ user_id
2. security_access_grant    action=create, user_id, modulo_code, role=owner
        ↓
3. security_managed_rfc     action=create, user_id, rfc, label
        ↓ managed_rfc_id
4. security_secret_store    managed_rfc_id, cer_b64, key_b64, key_password, modulo_code, owner_user_id
        ↓ secret_id
5. conta4all_sync_start     managed_rfc_id, rfc, cer_b64*, key_b64*, key_password*, fecha_inicio, fecha_fin, tipo
   (* en v2 vienen del vault vía security_secret_retrieve interno)
```

---

## Flujo de login

```
security_user_login  →  JWT (cookie httpOnly en el dashboard)
        ↓
security_user_session_verify  →  en cada ruta protegida del dashboard Next.js
```

---

## Modelo de cifrado — DEK/KEK

```
e.firma (cer + key + password)
    │
    ▼ DEK aleatoria 256-bit por secreto
AES-256-GCM → payload_cifrado (jsonb en platform.secrets)
    │
    ▼ KEK maestra (PLATFORM_KEK_V1, env var Render)
AES-256-GCM → dek_encrypted (en platform.secrets)

KEK NUNCA en Supabase. Rotación futura via kek_version.
```

---

## Skills internal_only (bloqueados en /run/ HTTP)

`security_secret_retrieve` y `security_support_decrypt_session` tienen `"internal_only": true`
en su `manifest.json`. `factory_api.py` devuelve 403 si se intenta llamar via HTTP directo.
Solo invocables desde otros skills via SkillRunner/importlib.

---

## Tablas Supabase (schema `platform`)

```sql
platform.users            id, email UNIQUE, password_hash, nombre, created_at
platform.modulos          code PK, nombre, activo
platform.access_grants    id, user_id FK, modulo_code FK, role, created_at — UNIQUE(user_id, modulo_code)
platform.secrets          id, modulo_code, owner_user_id FK, scope_type, scope_ref_id,
                          dek_encrypted, nonce_dek, kek_version, payload_cifrado jsonb, created_at
platform.password_resets  id, user_id FK, token_hash, expires_at, used
platform.login_attempts   id, email, ip, success, created_at
platform.audit_log        id, action, managed_rfc_id, actor, motivo, created_at
```

Inicializar DDL: `conta4all_cfdi_store action=setup_table dry_run=False`
(el DDL de `platform.*` se aplica vía `supabase_run_sql` apuntando a PLATFORM_*)

---

## Diferido a Fase 2

- SMTP para password reset y "romper cristal"
- 2FA (TOTP)
- `security_audit_log` con UI de revisión
- Captcha en login/registro
- Rotación de KEK (`kek_version`)
- Integración `vertical_payments` para access_grants automáticos vía Stripe
