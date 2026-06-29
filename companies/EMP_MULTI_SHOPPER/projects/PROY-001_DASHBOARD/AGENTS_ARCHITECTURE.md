# PROY-001 Dashboard

- company_id: `EMP_MULTI_SHOPPER`
- project_code: `PROY-001`
- module_code: `vertical_multi_shopper`
- schema: `multi_shopper`
- platform: `vercel`

El dashboard replica el patron Conta4All: Next.js dentro de `companies/<EMPRESA>/projects/<PROY>`, auth via `vertical_auth_security`, y datos via Factory API/data skills.

Reglas:
- No conectar Supabase desde el browser.
- No guardar tokens en codigo.
- No mover la logica reusable fuera de `factory/skills/internos/vertical_multi_shopper`.
- Vercel debe usar este directorio como root.
