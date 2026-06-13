# PROY-001 - AI Expense Capture Bot and Dashboard

PROY-001 is an operational expense module with a Telegram bot, AI/OCR receipt capture, Supabase storage, and a live Next.js dashboard. It is documented in English so it can be used as an Upwork portfolio example and as an internal technical handoff.

## Live Demo

| Asset | Value |
|---|---|
| Dashboard | `https://uc101-gastos.onrender.com` |
| Telegram bot | `@Duralon1_bot` |
| Factory API | `https://factory3.onrender.com` |
| Supabase schema | `uc101_proy001` |

## What Was Built

- Telegram bot for field expense capture.
- Guided manual expense registration.
- Quick expense capture from short messages.
- Receipt photo OCR with AI-assisted data extraction.
- ERP-ready Supabase schema.
- Next.js dashboard for KPIs, category analysis, editable records, and CSV export.
- Reusable Factory3 skills for backend business logic.

## Documentation Map

| File | Purpose |
|---|---|
| `UPWORK_CASE_STUDY.md` | Public-facing English portfolio case study and proposal copy |
| `deliverables.md` | Final delivery checklist |
| `closeout.md` | Technical closeout and handoff |
| `notes.md` | Internal project notes in English |
| `PROJECT_BRIEF.md` | Original internal brief |
| `project.json` | Project context and module metadata |

## Runtime Components

| Component | Path |
|---|---|
| Dashboard | `companies/EMP_DURALON/projects/PROY-001_GASTOS/dashboard/gastos/` |
| Telegram adapter | `factory/bots/duralon1_bot/bot.py` |
| Bot/runtime skill | `factory/skills/internos/vertical_client_expenses/client_expenses_run/` |
| Dashboard data skill | `factory/skills/internos/vertical_client_expenses/client_expenses_dashboard_data/` |

## Upwork Positioning

This project is a strong portfolio example for jobs involving Telegram bots, AI/OCR receipt processing, internal tools, Supabase dashboards, ERP-lite modules, and business process automation.
