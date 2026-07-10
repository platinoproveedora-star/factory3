# Notes - PROY-001

## Project Overview

PROY-001 is the first operational module delivered for the client: an expense capture and analysis system built around a Telegram bot, AI/OCR receipt processing, Supabase storage, and a business dashboard.

The first goal was not only to capture expenses. It was also to create a reusable foundation for future internal modules such as sales, inventory, billing, logistics, and ERP reporting.

## Initial Scope

- Telegram bot for expense capture.
- Receipt and ticket photo reading with AI/OCR.
- Manual capture through a guided form.
- Fast capture for simple expense messages.
- Business dashboard for expense analytics.
- Modular architecture so the same pattern can be reused for other departments.

## Confirmed Decisions

- Dedicated Telegram bot: `@Duralon1_bot`.
- Initial users: Tania, Luis, and ACH.
- Capture policy: no approval workflow in MVP; every authorized user can register expenses.
- User identity: Telegram chat ID.
- Export requirement: spreadsheet-friendly export from the dashboard.
- Dashboard deployment: Render.
- Backend runtime: Factory3 API on Render.
- Database: Supabase schema `uc101_proy001`.
- Storage: Supabase Storage bucket `uc101-proy001-assets`.

## Expense Categories

- combustible
- gastos varios
- taller mecanico
- papeleria
- telmex
- gas
- internet
- recargas celulares
- nomina
- gps
- imss
- sat
- ing. correa

## Key Risks Identified

- Low-quality receipt photos can reduce OCR accuracy.
- Ticket formats vary significantly between vendors.
- Category rules may need refinement after real production usage.
- Future role-based permissions may be needed as more users join.

## Implementation Notes

- Business logic lives in Factory3 skills, not in the Telegram adapter.
- Dashboard reads and writes through Factory API skills instead of owning database credentials.
- The expense schema includes ERP identity fields to support later integration.
- The module should remain sellable and reusable: project identity belongs in config/context, while generic behavior belongs in skills.

## Current Status

The module is operational, ERP-ready, and suitable for an Upwork portfolio/demo. The public-facing English case study is maintained in `UPWORK_CASE_STUDY.md`.
