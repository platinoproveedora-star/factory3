import { callSkill } from "@/lib/factory";

type Ctx = Record<string, unknown>;
type SkillResult<T = any> = { ok: boolean; data?: T; error?: string };

function run<T = any>(skill: string, context: Ctx): Promise<SkillResult<T>> {
  return callSkill(skill, context) as Promise<SkillResult<T>>;
}

// ── TRIPS4ALL ─────────────────────────────────────────────────────────────
export const tripCreate = (ctx: Ctx) => run("vertical_fleet4all_trips/trip_create", ctx);
export const expenseCapture = (ctx: Ctx) => run("vertical_fleet4all_trips/expense_capture", ctx);
export const tripClose = (ctx: Ctx) => run("vertical_fleet4all_trips/trip_close", ctx);
export const tripKpis = (ctx: Ctx) => run("vertical_fleet4all_trips/trip_kpis", ctx);

// ── COLLECT4ALL ───────────────────────────────────────────────────────────
export const paymentCapture = (ctx: Ctx) => run("vertical_fleet4all_collections/payment_capture", ctx);
export const receivablesSync = (ctx: Ctx) => run("vertical_fleet4all_collections/receivables_sync", ctx);
export const statementGenerate = (ctx: Ctx) => run("vertical_fleet4all_collections/statement_generate", ctx);
export const collectionReminder = (ctx: Ctx) => run("vertical_fleet4all_collections/collection_reminder", ctx);

// ── CARTAPORTE4ALL ────────────────────────────────────────────────────────
export const cartaporteBuild = (ctx: Ctx) => run("vertical_fleet4all_cartaporte/cartaporte_build", ctx);
export const cartaporteValidate = (ctx: Ctx) => run("vertical_fleet4all_cartaporte/cartaporte_validate", ctx);
export const pacStamp = (ctx: Ctx) => run("vertical_fleet4all_cartaporte/pac_stamp", ctx);
export const cartaporteCancel = (ctx: Ctx) => run("vertical_fleet4all_cartaporte/cartaporte_cancel", ctx);

// ── SETTLEMENTS4ALL ───────────────────────────────────────────────────────
export const advanceCapture = (ctx: Ctx) => run("vertical_fleet4all_settlements/advance_capture", ctx);
export const settlementCalculate = (ctx: Ctx) => run("vertical_fleet4all_settlements/settlement_calculate", ctx);
export const receiptGenerate = (ctx: Ctx) => run("vertical_fleet4all_settlements/receipt_generate", ctx);
export const settlementHistory = (ctx: Ctx) => run("vertical_fleet4all_settlements/settlement_history", ctx);

// ── FUEL4ALL ──────────────────────────────────────────────────────────────
export const fuelLoadCapture = (ctx: Ctx) => run("vertical_fleet4all_fuel/fuel_load_capture", ctx);
export const mileageCalculate = (ctx: Ctx) => run("vertical_fleet4all_fuel/mileage_calculate", ctx);
export const deviationAlert = (ctx: Ctx) => run("vertical_fleet4all_fuel/deviation_alert", ctx);

// ── MAINTENANCE4ALL ───────────────────────────────────────────────────────
export const maintenanceSchedule = (ctx: Ctx) => run("vertical_fleet4all_maintenance/maintenance_schedule", ctx);
export const serviceCapture = (ctx: Ctx) => run("vertical_fleet4all_maintenance/service_capture", ctx);
export const partsKardex = (ctx: Ctx) => run("vertical_fleet4all_maintenance/parts_kardex", ctx);
export const unitRecord = (ctx: Ctx) => run("vertical_fleet4all_maintenance/unit_record", ctx);

// ── QUOTES4ALL ────────────────────────────────────────────────────────────
export const rateManage = (ctx: Ctx) => run("vertical_fleet4all_quoting/rate_manage", ctx);
export const quoteBuild = (ctx: Ctx) => run("vertical_fleet4all_quoting/quote_build", ctx);
export const quotePdfSend = (ctx: Ctx) => run("vertical_fleet4all_quoting/quote_pdf_send", ctx);

// Fleet4All Ops
export const fleetDashboardSnapshot = (ctx: Ctx) => run("vertical_fleet4all_ops/fleet_dashboard_snapshot", ctx);
export const fleetOperationalData = (ctx: Ctx) => run("vertical_fleet4all_ops/fleet_operational_data", ctx);
