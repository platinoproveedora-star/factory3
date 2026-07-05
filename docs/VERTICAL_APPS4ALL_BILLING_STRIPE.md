# Apps4All Billing Stripe

Vertical Apps4All para planes, checkout y estado de suscripcion.

Contrato:
- `module_code` identifica el modulo vendible.
- `company_id` identifica la empresa compradora.
- `price_id` viene de config/contexto, no hardcode.
- Checkout real requiere `dry_run=false` y `confirm_billing=true`.

Skills:
- `vertical_apps4all_billing_stripe/apps4all_billing_plan`
- `vertical_apps4all_billing_stripe/apps4all_billing_checkout`
- `vertical_apps4all_billing_stripe/apps4all_billing_status`
