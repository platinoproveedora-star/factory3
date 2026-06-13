# Deliverables - PROY-001 - Expense Capture Bot and Dashboard

`EMP_DURALON` | `UC-101` legacy client | `module_code: gastos` | Repo: `platinoproveedora-star/uc101-proy001`

**Status:** ERP-ready and operational
**Closed:** 2026-06-01
**Last documentation review:** 2026-06-13

## Final Checklist

- [x] Telegram bot running through Factory3 with an active webhook.
- [x] Guided manual expense capture through `/nuevo`.
- [x] Fast manual capture for amount, date, and concept.
- [x] AI/OCR receipt capture from ticket photos using Anthropic Haiku vision.
- [x] Expense category suggestion from receipt images and text.
- [x] Supabase schema `uc101_proy001` with 5 ERP-ready tables.
- [x] 12 seeded expense categories.
- [x] `vehiculo` field for vehicle/unit-level expense tracking.
- [x] Next.js dashboard deployed at `https://uc101-gastos.onrender.com`.
- [x] Monthly KPIs, category comparisons, monthly comparison, and category by month matrix.
- [x] Inline editable expense table with create, update, and delete support.
- [x] Sortable expense table.
- [x] CSV export from the dashboard.
- [x] ERP health check passed for required identity fields and folios.
- [x] ERP link fields on expenses: `cost_center_id`, `customer_id`, `supplier_id`, `sales_order_id`, `purchase_order_id`, `asset_id`, `erp_tags`.
- [x] User records prepared with `global_user_id` and `modules_allowed`.
- [x] Tania pre-registered as `USR-002`.
- [x] ACH registered as `USR-003`.
- [x] CORS enabled in Factory3 for external dashboard requests.

## Delivered URLs and Resources

| Resource | Value |
|---|---|
| Dashboard | `https://uc101-gastos.onrender.com` |
| Telegram bot | `@Duralon1_bot` |
| GitHub repo | `https://github.com/platinoproveedora-star/uc101-proy001` |
| Supabase schema | `uc101_proy001` |
| Factory API | `https://factory3.onrender.com` |
| Dashboard source | `companies/EMP_DURALON/projects/PROY-001_GASTOS/dashboard/gastos/` |
| Bot source | `factory/bots/duralon1_bot/bot.py` |
| Runtime skill | `vertical_client_expenses/client_expenses_run` |
| Dashboard data skill | `vertical_client_expenses/client_expenses_dashboard_data` |

## Non-Blocking Post-Close Items

- [ ] Luis Telegram chat ID is registered automatically after his first `/start`.
- [ ] Confirm Supabase Storage bucket `uc101-proy001-assets` remains active for receipt assets.

## Upwork Delivery Notes

This module can be presented as a completed production MVP: Telegram bot, AI receipt OCR, ERP-ready database schema, and business dashboard. The public case study is in `UPWORK_CASE_STUDY.md` and avoids private client contact details.
