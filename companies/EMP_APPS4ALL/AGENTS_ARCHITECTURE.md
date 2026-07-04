# Apps4All — Architecture agent notes

This document summarizes Apps4All structure under `companies/EMP_APPS4ALL/`, including multi-tenancy, schemas, and current related skills.

- Multi-tenant SaaS platform
- Identity schema: `platform` (users, companies, access_grants)
- Domain schema: `apps4all` (clients, orders, support_tickets, integrations)
- Legacy v1 coexists in `apps4all_legacy`

Current related skills
- `vertical_apps4all/platform_account_inspect` — read-only inspection over `platform`
- `vertical_auth_security/security_user_login`
- `vertical_auth_security/security_user_register`
- `vertical_auth_security/security_access_grant`
- `vertical_saas/saas_admin_data`

Risk notes
- Schemas `platform` and `apps4all` are shared surfaces; new skills must keep `schema=platform` / `schema=apps4all` explicit.
- `platform.secrets` must remain `internal_only: true`.
- Legacy v1 tables/names must remain untouched until full migration.

Rule for future changes
- New company-owned features must add `company_id=EMP_APPS4ALL` filters explicitly in every query.
- Any change in `platform` requires PR review with regard to all apps.

