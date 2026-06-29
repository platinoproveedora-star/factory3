# EMP_MULTI_SHOPPER / PROY-001 Dashboard

Dashboard Next.js operativo para `vertical_multi_shopper` / Purchasing IA Engine.

Produccion:

```text
https://multi-shopper.vercel.app
```

## Deploy Vercel

Root directory:

```text
companies/EMP_MULTI_SHOPPER/projects/PROY-001_DASHBOARD
```

Variables requeridas:

```text
FACTORY_API_URL
FACTORY_API_SECRET
PLATFORM_JWT_SECRET
MULTI_SHOPPER_MODULE_CODE
MULTI_SHOPPER_SCHEMA
MULTI_SHOPPER_COMPANY_ID
MULTI_SHOPPER_PROJECT_CODE
MULTI_SHOPPER_WRITE_KEY
MULTI_SHOPPER_STORAGE_BUCKET
```

El dashboard llama Factory API desde API routes/server components. No expone credenciales Supabase en browser.
