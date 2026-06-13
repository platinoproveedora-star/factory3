# Upwork Case Study - AI Telegram Expense Capture Bot and ERP-Ready Dashboard

## One-Line Summary

Built a production MVP that lets field users register company expenses from Telegram, extract receipt data with AI/OCR, store the records in Supabase, and review the operation from a live Next.js dashboard.

## Project Type

- Business automation
- Telegram bot
- AI/OCR receipt processing
- Internal operations dashboard
- Supabase database design
- ERP-ready module architecture

## Client Problem

The client needed a simple way for operational staff to record expenses without opening a complex ERP screen. Expenses were being generated in the field, often with paper tickets or quick notes, and the business needed a central place to review totals, categories, vehicles, and monthly trends.

The solution had to be fast enough for daily use, simple enough for non-technical users, and structured enough to become part of a larger ERP later.

## Delivered Solution

I built a Telegram-first expense capture system connected to an ERP-ready data model and a web dashboard:

- Field users register expenses directly from Telegram.
- The bot supports guided manual capture and quick text capture.
- Users can send receipt/ticket photos for AI/OCR extraction.
- Expenses are stored in Supabase with company, project, module, and folio fields.
- A Next.js dashboard shows KPIs, tables, comparisons, and exportable data.
- Backend logic runs through reusable Factory3 skills, so the dashboard and bot share the same business layer.

## Core Features

### Telegram Bot

- `/start` onboarding.
- `/nuevo` guided expense capture.
- Quick expense capture from short messages.
- Receipt photo capture with AI/OCR.
- Expense category suggestion.
- User identification by Telegram chat ID.
- User-level summaries and recent expenses.

### Dashboard

- Current month expense KPIs.
- Expense count and totals.
- Category totals.
- Current month vs prior month comparison.
- Category by month matrix.
- Editable expense table.
- Add, edit, and delete expenses from the dashboard.
- Sortable records.
- CSV export for spreadsheet workflows.

### Database and ERP Readiness

- Dedicated Supabase schema for the module.
- ERP identity fields: company, project, module, and folio.
- Future integration fields for customers, suppliers, orders, assets, and cost centers.
- Vehicle/unit tracking field for operational expense analysis.
- User records prepared for global user identity across modules.

## Architecture

```text
Telegram user
  -> Telegram bot webhook
  -> Factory3 FastAPI runtime
  -> vertical_client_expenses/client_expenses_run
  -> Supabase schema
  -> Next.js dashboard
  -> vertical_client_expenses/client_expenses_dashboard_data
```

## Tech Stack

- Telegram Bot API
- Python
- FastAPI
- Factory3 skill runtime
- Supabase Postgres
- Supabase Storage
- Anthropic Haiku vision for receipt extraction
- Next.js
- TypeScript
- Tailwind CSS
- Render deployment

## Why This Is Valuable

This is more than a simple dashboard. It combines field capture, AI extraction, structured data, and management reporting in one workflow. The client can collect cleaner expense data without forcing staff into an ERP, while still keeping the database ready for future ERP modules.

## Reusable Pattern

The same architecture can be reused for:

- Purchase receipts
- Delivery proofs
- Field service reports
- Maintenance logs
- Sales order capture
- Payment proof uploads
- Operations checklists

The important pattern is: chat-based capture for field users, reusable backend skills for business logic, structured Supabase storage, and a focused dashboard for managers.

## Demo Assets

| Asset | Value |
|---|---|
| Live dashboard | `https://uc101-gastos.onrender.com` |
| Telegram bot | `@Duralon1_bot` |
| Backend runtime | `https://factory3.onrender.com` |
| Source location | `companies/EMP_DURALON/projects/PROY-001_GASTOS/` |

## Portfolio Description

I designed and built an AI-assisted expense capture system for a business operations team. The system allows employees to register expenses from Telegram using manual input or receipt photos. AI/OCR extracts key receipt information and stores it in a structured Supabase schema. Managers can review expenses in a live Next.js dashboard with KPIs, category breakdowns, monthly comparisons, editable records, and CSV export.

The backend was implemented as reusable Factory3 skills so the bot and dashboard share the same business logic. The database was designed with ERP-ready identity fields, making the module ready to connect with sales, inventory, billing, and purchasing modules later.

## Upwork Proposal Angle

Use this project when applying to jobs that mention:

- Telegram bot development
- Business process automation
- Receipt OCR
- Expense tracking
- Supabase dashboards
- Internal tools
- ERP-lite systems
- AI automation for operations teams

Short proposal paragraph:

```text
I recently built a production expense capture system that combines a Telegram bot, AI/OCR receipt extraction, Supabase, and a live Next.js dashboard. Field users can send expenses or receipt photos from Telegram, while managers review KPIs, categories, monthly comparisons, and editable records in the dashboard. The backend is modular and ERP-ready, so the same pattern can be reused for expenses, payments, purchase receipts, delivery proofs, or field reports.
```

## Handoff Status

- Bot is operational.
- Dashboard is deployed.
- Database schema is ERP-ready.
- Delivery checklist is complete.
- Non-blocking follow-ups are documented in `deliverables.md` and `closeout.md`.
